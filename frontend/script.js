const fetchBtn = document.getElementById('fetchBtn');
const startBtn = document.getElementById('startBtn');
const urlInput = document.getElementById('urlInput');
const selectionSection = document.getElementById('selectionSection');
const uniList = document.getElementById('uniList');
const selectAllCheckbox = document.getElementById('selectAll');
const selectedCountSpan = document.getElementById('selectedCount');
const statusSection = document.getElementById('statusSection');
const progressBar = document.getElementById('progressBar');
const statusText = document.getElementById('statusText');
const resultSection = document.getElementById('resultSection');
const downloadBtn = document.getElementById('downloadBtn');

let currentJobId = null;
let pollInterval = null;
let universities = [];

fetchBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
        alert('請輸入網址');
        return;
    }

    fetchBtn.disabled = true;
    fetchBtn.textContent = '取得列表中...';

    try {
        const response = await fetch('/api/fetch_universities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) throw new Error('無法取得學校列表');

        const data = await response.json();
        universities = data.universities;
        renderUniList(universities);

        selectionSection.classList.remove('hidden');
        fetchBtn.textContent = '1. 取得學校列表 (已完成)';

    } catch (error) {
        console.error(error);
        alert('錯誤: ' + error.message);
        fetchBtn.disabled = false;
        fetchBtn.textContent = '1. 取得學校列表';
    }
});

function renderUniList(unis) {
    uniList.innerHTML = '';
    unis.forEach((uni, index) => {
        const div = document.createElement('div');
        div.className = 'uni-item'; // Use 'label' in CSS but div here for flex
        div.innerHTML = `
            <label style="display:flex; align-items:center; width:100%; cursor:pointer;">
                <input type="checkbox" value="${uni.name}" checked>
                <span style="margin-left:5px">${uni.name}</span>
            </label>
        `;
        uniList.appendChild(div);
    });

    updateSelectedCount();

    // Add event listeners to checkboxes
    const checkboxes = uniList.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.addEventListener('change', updateSelectedCount));
}

selectAllCheckbox.addEventListener('change', (e) => {
    const checkboxes = uniList.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = e.target.checked);
    updateSelectedCount();
});

function updateSelectedCount() {
    const checkboxes = uniList.querySelectorAll('input[type="checkbox"]');
    const checked = Array.from(checkboxes).filter(cb => cb.checked);
    selectedCountSpan.textContent = `已選: ${checked.length}`;
    startBtn.disabled = checked.length === 0;
}

startBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();

    // Get selected universities
    const checkboxes = uniList.querySelectorAll('input[type="checkbox"]');
    const selectedTargets = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    if (selectedTargets.length === 0) {
        alert('請至少選擇一間學校');
        return;
    }

    // Reset UI
    startBtn.disabled = true;
    startBtn.textContent = '分析中...';
    resultSection.classList.add('hidden');
    statusSection.classList.remove('hidden');
    progressBar.style.width = '0%';
    statusText.textContent = '正在啟動爬蟲...';

    // Scroll to status
    statusSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, targets: selectedTargets })
        });

        if (!response.ok) {
            throw new Error('啟動失敗');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Start polling
        pollInterval = setInterval(checkStatus, 1000);

    } catch (error) {
        console.error(error);
        alert('發生錯誤: ' + error.message);
        startBtn.disabled = false;
        startBtn.textContent = '2. 開始分析選定學校';
    }
});

async function checkStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/status/${currentJobId}`);
        if (!response.ok) return;

        const data = await response.json();

        // Update UI
        progressBar.style.width = `${data.progress}%`;
        statusText.textContent = `${data.message} (${data.progress}%)`;

        if (data.status === 'completed') {
            clearInterval(pollInterval);
            finishJob(data.filename);
        } else if (data.status === 'error') {
            clearInterval(pollInterval);
            alert(data.message);
            resetUI();
        }

    } catch (error) {
        console.error('Polling error:', error);
    }
}

function finishJob(filename) {
    statusSection.classList.add('hidden');
    resultSection.classList.remove('hidden');
    startBtn.disabled = false;
    startBtn.textContent = '開始分析';

    // Fetch and show preview
    fetchPreview();

    // Set up download button
    downloadBtn.onclick = () => {
        window.location.href = `/api/download/${currentJobId}`;
    };
}

async function fetchPreview() {
    try {
        const response = await fetch(`/api/preview/${currentJobId}`);
        if (!response.ok) return;
        const data = await response.json();
        const rows = data.preview;

        if (rows && rows.length > 0) {
            const previewContainer = document.getElementById('previewContainer');
            const tbody = document.querySelector('#previewTable tbody');
            tbody.innerHTML = '';

            rows.forEach(row => {
                const tr = document.createElement('tr');
                // Construct standard string for preview
                const standards = [
                    row['國文檢定標準'] ? `國:${row['國文檢定標準']}` : '',
                    row['英文檢定標準'] ? `英:${row['英文檢定標準']}` : '',
                    row['數學A檢定標準'] ? `數A:${row['數學A檢定標準']}` : '',
                    row['數學B檢定標準'] ? `數B:${row['數學B檢定標準']}` : '',
                    row['社會檢定標準'] ? `社:${row['社會檢定標準']}` : '',
                    row['自然檢定標準'] ? `自:${row['自然檢定標準']}` : ''
                ].filter(Boolean).join(', ');

                tr.innerHTML = `
                    <td>${row['學校名稱']}</td>
                    <td>${row['學系名稱']}</td>
                    <td>${row['招生名額']}</td>
                    <td>${standards}</td>
                `;
                tbody.appendChild(tr);
            });

            previewContainer.classList.remove('hidden');
        }
    } catch (e) {
        console.error("Failed to load preview", e);
    }
}

function resetUI() {
    startBtn.disabled = false;
    startBtn.textContent = '開始分析';
    statusSection.classList.add('hidden');
}
