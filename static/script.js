document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // STATE & DOM ELEMENTS
    // =================================================================

    let currentFile = null;

    const dom = {
        // The 'loader' element is now the splash container
        splashContainer: document.querySelector('.splash-container'),
        glamoContent: document.getElementById('glamo-content'),
        editForm: document.getElementById('editForm'),
        photoInput: document.getElementById('photo'),
        fileInfo: document.getElementById('fileInfo'),
        photoPreview: document.getElementById('photoPreview'),
        fileName: document.getElementById('fileName'),
        styleSelector: document.getElementById('styleSelector'),
        styleDescription: document.getElementById('styleDescription'),
        suggestStyleBtn: document.getElementById('suggestStyleBtn'),
        styleAppResult: document.getElementById('styleAppResult'),
        loadingSpinner: document.getElementById('loading'),
        resultBlock: document.getElementById('result'),
        errorMessageDiv: document.getElementById('errorMessage'),
        moodInfoDiv: document.getElementById('moodInfo'),
        editingValuesDiv: document.getElementById('editingValues'),
        captionListDiv: document.getElementById('captionList'),
        songListDiv: document.getElementById('songList')
    };

    // =================================================================
    // API CALLS
    // =================================================================
    async function analyzeImage(formData) {
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.detail || 'An unknown server error occurred.');
        }
        return result;
    }

    async function suggestStyle(formData) {
        const response = await fetch('/suggest_style_app', { method: 'POST', body: formData });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.detail || 'Failed to get a style suggestion.');
        }
        return result;
    }

    // =================================================================
    // UI RENDERING & UPDATES
    // =================================================================
    function setLoadingState(isLoading) {
        dom.loadingSpinner.style.display = isLoading ? 'flex' : 'none';
        if (isLoading) {
            dom.resultBlock.style.display = 'none';
            dom.errorMessageDiv.style.display = 'none';
        }
    }

    function renderError(message) {
        dom.errorMessageDiv.textContent = `❌ ${message}`;
        dom.errorMessageDiv.style.display = 'block';
        dom.errorMessageDiv.scrollIntoView({ behavior: 'smooth' });
    }

    function renderResults(result) {
        // Clear previous results
        dom.moodInfoDiv.innerHTML = '';
        dom.editingValuesDiv.innerHTML = '';
        dom.captionListDiv.innerHTML = '';
        dom.songListDiv.innerHTML = '';

        // Render sections
        renderEditingSteps(result.editing_values);
        renderCaptions(result.captions);
        renderSongs(result.songs);
        renderAnalysis(result.mood_info);

        // Show results and manage focus for accessibility
        dom.resultBlock.style.display = 'block';
        dom.resultBlock.scrollIntoView({ behavior: 'smooth', block: 'start' });
        dom.resultBlock.focus();

        initializeTilt();
    }

    function renderAnalysis(moodInfo) {
        const template = document.getElementById('analysis-card-template');
        if (!moodInfo || !template) {
            dom.moodInfoDiv.innerHTML = '<p>No image analysis available.</p>';
            return;
        }

        const analysisPoints = moodInfo.split('\n')
            .map(line => line.replace(/-\s*/, '').trim())
            .filter(line => line.includes(':'));

        if (analysisPoints.length === 0) {
            dom.moodInfoDiv.innerHTML = '<p>No analysis points found.</p>';
            return;
        }

        analysisPoints.forEach(point => {
            const card = template.content.cloneNode(true);
            const textElement = card.querySelector('.analysis-text');
            const [key, ...valueParts] = point.split(':');
            const value = valueParts.join(':').trim();

            textElement.innerHTML = `<strong>${key.replace(/\*\*/g, '')}:</strong> <i>${value}</i>`;
            dom.moodInfoDiv.appendChild(card);
        });
    }

    function renderEditingSteps(editingValues) {
        const template = document.getElementById('editing-card-template');
        if (!editingValues || !template) {
            dom.editingValuesDiv.innerHTML = '<p>No editing steps provided.</p>';
            return;
        }

        const lines = editingValues.split('\n').filter(line => line.trim());
        if (lines.length === 0) {
            dom.editingValuesDiv.innerHTML = '<p>No editing steps detected.</p>';
            return;
        }

        lines.forEach(line => {
            const card = template.content.cloneNode(true);
            const textElement = card.querySelector('.editing-text');

            const match = line.match(/\*\*(.*?)\*\*\s*(.*)/);

            if (match) {
                const step = match[1];
                const reason = match[2];
                textElement.innerHTML = `<strong>${step}</strong> <i>${reason}</i>`;
            } else {
                textElement.textContent = line;
            }

            dom.editingValuesDiv.appendChild(card);
        });
    }

    function renderCaptions(captions) {
        const template = document.getElementById('caption-card-template');
        if (!captions || captions.length === 0 || !template) {
            dom.captionListDiv.innerHTML = '<p>No captions were generated.</p>';
            return;
        }
        captions.forEach(caption => {
            const card = template.content.cloneNode(true);
            const span = card.querySelector('span');
            span.textContent = caption;

            const button = card.querySelector('.copy-btn');
            button.addEventListener('click', () => copyToClipboard(caption, button));

            dom.captionListDiv.appendChild(card);
        });
    }

    function renderSongs(songs) {
        const template = document.getElementById('song-card-template');
        if (!songs || songs.length === 0 || !template) {
            dom.songListDiv.innerHTML = '<p>No music suggestions found for this image.</p>';
            return;
        }
        songs.forEach(song => {
            const card = template.content.cloneNode(true);
            card.querySelector('img').src = song.image || '/static/music-default.jpg';
            card.querySelector('img').alt = `Album art for ${song.title} by ${song.artist}`;
            card.querySelector('.song-title').textContent = song.title || 'Untitled';
            card.querySelector('.song-artist').textContent = song.artist || 'Unknown Artist';
            const audio = card.querySelector('audio');
            if (song.preview) {
                audio.src = song.preview;
            } else {
                audio.remove();
            }
            dom.songListDiv.appendChild(card);
        });
    }

    // =================================================================
    // UTILITY FUNCTIONS
    // =================================================================

    async function compressImage(file) {
        if (!file || !file.type.startsWith('image/')) return file;
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = (e) => {
                const img = new Image();
                img.src = e.target.result;
                img.onload = () => {
                    const max = 1024;
                    const scale = Math.min(max / img.width, max / img.height, 1);
                    const canvas = document.createElement("canvas");
                    canvas.width = img.width * scale;
                    canvas.height = img.height * scale;
                    const ctx = canvas.getContext("2d");
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob((blob) => resolve(new File([blob], "compressed.webp", { type: "image/webp" })), "image/webp", 0.85);
                };
                img.onerror = () => resolve(file);
            };
        });
    }

    function copyToClipboard(textToCopy, buttonElement) {
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = buttonElement.textContent;
            buttonElement.textContent = 'Copied!';
            buttonElement.disabled = true;
            setTimeout(() => {
                buttonElement.textContent = originalText;
                buttonElement.disabled = false;
            }, 1500);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            renderError('Could not copy text to clipboard.');
        });
    }

    // =================================================================
    // EVENT HANDLERS
    // =================================================================

    async function handleFormSubmit(event) {
        event.preventDefault();
        if (!currentFile) {
            renderError('Please upload a photo before submitting.');
            return;
        }

        setLoadingState(true);
        const compressedPhoto = await compressImage(currentFile);

        const formData = new FormData();
        formData.append('photo', compressedPhoto);
        formData.append('selected_app', dom.editForm.elements.selected_app.value);
        formData.append('style', dom.editForm.elements.style.value);

        try {
            const result = await analyzeImage(formData);
            renderResults(result);
        } catch (error) {
            console.error('Fetch Error:', error);
            renderError(error.message);
        } finally {
            setLoadingState(false);
        }
    }

    async function handleSuggestStyle() {
        if (!currentFile) {
            renderError("Please upload a photo before suggesting a style.");
            return;
        }

        dom.styleAppResult.style.display = 'block';
        dom.styleAppResult.textContent = '⏳ Analyzing for best style...';

        const compressedPhoto = await compressImage(currentFile);
        const formData = new FormData();
        formData.append('photo', compressedPhoto);

        try {
            const result = await suggestStyle(formData);
            dom.styleAppResult.innerHTML = `<pre>${result.result}</pre>`;
        } catch (error) {
            console.error('Style Suggestion Error:', error);
            dom.styleAppResult.textContent = `❌ ${error.message}`;
        }
    }

    function handlePhotoPreview(file) {
        if (file) {
            dom.photoPreview.src = URL.createObjectURL(file);
            dom.fileName.textContent = file.name;
            dom.fileInfo.style.display = 'flex';
        }
    }

    function handleStyleDescriptionChange() {
        const selectedOption = dom.styleSelector.options[dom.styleSelector.selectedIndex];
        dom.styleDescription.textContent = selectedOption.dataset.desc || '';
    }

    // =================================================================
    // INITIAL SETUP & EVENT LISTENERS
    // =================================================================

    // --- SPLASH SCREEN LOGIC (Replaces old window.onload) ---
    const body = document.body;
    body.classList.add('splash-active');

    setTimeout(() => {
        if (dom.splashContainer) {
            dom.splashContainer.style.transition = 'opacity 0.5s ease-out';
            dom.splashContainer.style.opacity = '0';
        }

        setTimeout(() => {
            if (dom.splashContainer) {
                dom.splashContainer.style.display = 'none';
            }
            body.classList.remove('splash-active');

            if (dom.glamoContent) {
                dom.glamoContent.style.display = 'block';
                initializeTilt();
            }
        }, 500);

    }, 3500);
    // --- END SPLASH SCREEN LOGIC ---

    if (dom.editForm) dom.editForm.addEventListener('submit', handleFormSubmit);
    if (dom.suggestStyleBtn) dom.suggestStyleBtn.addEventListener('click', handleSuggestStyle);
    if (dom.styleSelector) dom.styleSelector.addEventListener('change', handleStyleDescriptionChange);

    if (dom.photoInput) {
        dom.photoInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                currentFile = file;
                handlePhotoPreview(currentFile);
            }
            e.target.value = null;
        });
    }
});