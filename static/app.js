document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons on load
    lucide.createIcons();

    // DOM Elements
    const navTabs = document.querySelectorAll(".nav-tab");
    const viewSections = document.querySelectorAll(".view-section");
    
    const freeTierWarn = document.getElementById("free-tier-warn");
    const btnCloseBanner = document.getElementById("btn-close-banner");
    
    const dropZone = document.getElementById("drop-zone");
    const videoInput = document.getElementById("video-input");
    const fileNameDisplay = document.getElementById("file-name-display");
    const extractForm = document.getElementById("extract-form");
    const btnSubmit = document.getElementById("btn-submit");

    // Batch Queue DOM elements
    const batchQueueContainer = document.getElementById("batch-queue-container");
    const batchQueueList = document.getElementById("batch-queue-list");
    const batchDelayInput = document.getElementById("batch-delay-input");
    const batchDelayVal = document.getElementById("batch-delay-val");
    const batchProgressContainer = document.getElementById("batch-progress-container");
    const batchProgressStatus = document.getElementById("batch-progress-status");
    const batchProgressPercent = document.getElementById("batch-progress-percent");
    const batchProgressBarFill = document.getElementById("batch-progress-bar-fill");
    const btnAbortBatch = document.getElementById("btn-abort-batch");
    const processingStepsChecklist = document.getElementById("processing-steps-checklist");
    const singleProgressContainer = document.getElementById("single-progress-container");
    const singleProgressPercent = document.getElementById("single-progress-percent");
    const singleProgressBarFill = document.getElementById("single-progress-bar-fill");
    const processingTitle = document.getElementById("processing-title");
    const processingDetail = document.getElementById("processing-detail");
    
    // Status States
    const stateIdle = document.getElementById("state-idle");
    const stateProcessing = document.getElementById("state-processing");
    const stateResult = document.getElementById("state-result");
    const stateError = document.getElementById("state-error");
    
    // Result details
    const resultStatus = document.getElementById("result-status");
    const resultTitle = document.getElementById("result-title");
    const resultPeopleContainer = document.getElementById("result-people-container");
    const resultMetadata = document.getElementById("result-metadata");
    
    // Error details
    const errorMessage = document.getElementById("error-message");
    
    // History
    const btnRefreshHistory = document.getElementById("btn-refresh-history");
    const historyGrid = document.getElementById("history-grid");
    const historyDetailModal = document.getElementById("history-detail-modal");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const modalRunTitle = document.getElementById("modal-run-title");
    const modalPeopleContainer = document.getElementById("modal-people-container");
    const modalMetadata = document.getElementById("modal-metadata");

    // Custom Dialog DOM Elements
    const confirmModal = document.getElementById("confirm-modal");
    const confirmModalMessage = document.getElementById("confirm-modal-message");
    const confirmModalCancel = document.getElementById("confirm-modal-cancel");
    const confirmModalOk = document.getElementById("confirm-modal-ok");
    const constellationHint = document.getElementById("constellation-hint");
    const btnCloseHint = document.getElementById("btn-close-hint");

    let confirmResolver = null;

    // Toast Notification System
    function showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let iconName = "info";
        if (type === "success") iconName = "check-circle";
        if (type === "error") iconName = "alert-circle";
        if (type === "warning") iconName = "alert-triangle";

        toast.innerHTML = `
            <div class="toast-icon"><i data-lucide="${iconName}"></i></div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" aria-label="Close message">&times;</button>
        `;

        container.appendChild(toast);
        lucide.createIcons();

        // Animate in
        setTimeout(() => {
            toast.classList.add("show");
        }, 10);

        // Auto close after 4s
        const autoCloseTimeout = setTimeout(() => {
            closeToast(toast);
        }, 4000);

        // Bind close button
        const closeBtn = toast.querySelector(".toast-close");
        closeBtn.addEventListener("click", () => {
            clearTimeout(autoCloseTimeout);
            closeToast(toast);
        });
    }

    function closeToast(toast) {
        toast.classList.remove("show");
        toast.classList.add("hide");
        toast.addEventListener("transitionend", () => {
            toast.remove();
        });
    }

    // Custom Confirm Modal Dialog
    function showConfirm(message, isDestructive = false) {
        return new Promise((resolve) => {
            confirmResolver = resolve;
            if (confirmModalMessage) confirmModalMessage.textContent = message;
            
            if (confirmModalOk) {
                if (isDestructive) {
                    confirmModalOk.className = "btn-primary btn-danger-fill";
                } else {
                    confirmModalOk.className = "btn-primary";
                }
            }
            
            if (confirmModal) {
                confirmModal.classList.add("active");
                confirmModal.setAttribute("aria-hidden", "false");
            }
        });
    }

    function closeConfirmModal(result) {
        if (confirmModal) {
            confirmModal.classList.remove("active");
            confirmModal.setAttribute("aria-hidden", "true");
        }
        if (confirmResolver) {
            confirmResolver(result);
            confirmResolver = null;
        }
    }

    if (confirmModalCancel) {
        confirmModalCancel.addEventListener("click", () => closeConfirmModal(false));
    }
    if (confirmModalOk) {
        confirmModalOk.addEventListener("click", () => closeConfirmModal(true));
    }
    if (confirmModal) {
        confirmModal.addEventListener("click", (e) => {
            if (e.target === confirmModal) {
                closeConfirmModal(false);
            }
        });
    }

    // Video Player Modal
    const videoModal = document.getElementById("video-modal");
    const videoPlayer = document.getElementById("video-player");
    const videoModalTitle = document.getElementById("video-modal-title");
    const btnCloseVideoModal = document.getElementById("btn-close-video-modal");

    function openVideoModal(runId, videoName) {
        if (!videoModal || !videoPlayer) return;
        videoPlayer.src = `/api/runs/${runId}/video`;
        videoModalTitle.textContent = videoName || "Video Playback";
        videoModal.classList.add("active");
    }

    function closeVideoModal() {
        if (!videoModal || !videoPlayer) return;
        videoModal.classList.remove("active");
        videoPlayer.pause();
        videoPlayer.removeAttribute("src");
        videoPlayer.load();
    }

    if (btnCloseVideoModal) {
        btnCloseVideoModal.addEventListener("click", closeVideoModal);
    }
    if (videoModal) {
        videoModal.addEventListener("click", (e) => {
            if (e.target === videoModal) {
                closeVideoModal();
            }
        });
    }

    // Global event delegation for video link buttons
    document.addEventListener("click", (e) => {
        const videoLink = e.target.closest(".btn-video-link[data-run-id], .btn-video-link-sm[data-run-id]");
        if (videoLink) {
            e.preventDefault();
            e.stopPropagation();
            const runId = videoLink.getAttribute("data-run-id");
            const videoName = videoLink.getAttribute("data-video-name") || "Video";
            openVideoModal(runId, videoName);
        }
    });

    // Local Variables
    let selectedFiles = [];
    let isBatchActive = false;
    let currentBatchIndex = 0;
    let abortController = null;
    let listHoveredPoint = null;
    let activePollInterval = null;
    let searchQuery = "";

    // --- Tab Switching Navigation ---
    navTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const targetViewId = tab.getAttribute("data-view");
            localStorage.setItem("wovely-current-view", targetViewId);
            
            // Switch tabs active state
            navTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            
            // Switch section active state
            viewSections.forEach(section => {
                section.classList.remove("active");
                if (section.id === targetViewId) {
                    section.classList.add("active");
                }
            });

            // Load history if switched to history tab
            if (targetViewId === "view-history") {
                loadHistory();
            } else if (targetViewId === "view-constellation") {
                loadConstellation();
            }
        });
    });

    // Restore persisted tab view
    const persistedView = localStorage.getItem("wovely-current-view");
    if (persistedView) {
        const matchingTab = Array.from(navTabs).find(t => t.getAttribute("data-view") === persistedView);
        if (matchingTab) {
            matchingTab.click();
        }
    }

    // --- Banner Close ---
    if (btnCloseBanner) {
        btnCloseBanner.addEventListener("click", () => {
            freeTierWarn.style.display = "none";
        });
    }

    // --- Window-level Drag & Drop Default Prevention ---
    window.addEventListener("dragover", (e) => {
        e.preventDefault();
    });
    window.addEventListener("drop", (e) => {
        e.preventDefault();
    });

    // --- Drag & Drop Handlers ---
    dropZone.addEventListener("click", () => {
        videoInput.click();
    });

    videoInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files);
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files);
        }
    });

    // Slider listener
    if (batchDelayInput && batchDelayVal) {
        batchDelayInput.addEventListener("input", (e) => {
            batchDelayVal.textContent = `${e.target.value}s`;
        });
    }

    // Export CSV listener
    const btnExportCsv = document.getElementById("btn-export-csv");
    if (btnExportCsv) {
        btnExportCsv.addEventListener("click", () => {
            window.location.href = "/api/export";
        });
    }

    // Constellation search listener
    const constellationSearch = document.getElementById("constellation-search");
    if (constellationSearch) {
        constellationSearch.addEventListener("input", (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            drawConstellation();
        });
    }

    function handleFileSelection(files) {
        selectedFiles = Array.from(files).filter(file => file.type.startsWith("video/"));
        
        if (selectedFiles.length > 0) {
            if (selectedFiles.length === 1) {
                const file = selectedFiles[0];
                fileNameDisplay.textContent = `Selected: ${file.name} (${formatBytes(file.size)})`;
                batchQueueContainer.style.display = "none";
            } else {
                fileNameDisplay.textContent = `Selected ${selectedFiles.length} videos for batch extraction.`;
                renderQueueList();
                batchQueueContainer.style.display = "block";
            }
            btnSubmit.disabled = false;
        } else {
            showToast("Please select one or more valid video files.", "error");
            selectedFiles = [];
            fileNameDisplay.textContent = "";
            batchQueueContainer.style.display = "none";
            btnSubmit.disabled = true;
        }
    }

    function renderQueueList() {
        if (!batchQueueList) return;
        batchQueueList.innerHTML = "";
        selectedFiles.forEach((file, index) => {
            const item = document.createElement("div");
            item.className = "queue-item";
            item.id = `queue-item-${index}`;
            
            const nameSpan = document.createElement("span");
            nameSpan.className = "queue-item-name";
            nameSpan.textContent = file.name;
            nameSpan.title = file.name;
            
            const badgeSpan = document.createElement("span");
            badgeSpan.className = "queue-item-badge pending";
            badgeSpan.textContent = "Pending";
            badgeSpan.id = `queue-badge-${index}`;
            
            item.appendChild(nameSpan);
            item.appendChild(badgeSpan);
            batchQueueList.appendChild(item);
        });
    }

    function switchResultState(state) {
        stateIdle.classList.remove("active");
        stateProcessing.classList.remove("active");
        stateResult.classList.remove("active");
        stateError.classList.remove("active");

        if (state === "idle") stateIdle.classList.add("active");
        if (state === "processing") stateProcessing.classList.add("active");
        if (state === "result") stateResult.classList.add("active");
        if (state === "error") stateError.classList.add("active");
        
        lucide.createIcons();
    }

    function updateQueueItemStatus(index, badgeClass, text) {
        const badge = document.getElementById(`queue-badge-${index}`);
        if (badge) {
            badge.className = `queue-item-badge ${badgeClass}`;
            badge.textContent = text;
        }
    }

    // --- Form Submission ---
    extractForm.addEventListener("submit", (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0) return;

        if (selectedFiles.length === 1) {
            // Single file processing
            isBatchActive = false;
            singleProgressContainer.style.display = "block";
            batchProgressContainer.style.display = "none";
            btnAbortBatch.style.display = "none";
            processingTitle.textContent = "Analyzing Video...";
            processingDetail.textContent = "Uploading file via File API and querying Gemini. Please do not close this window.";
            switchResultState("processing");
            
            uploadSingleFile(selectedFiles[0]);
        } else {
            // Batch processing
            isBatchActive = true;
            currentBatchIndex = 0;
            abortController = new AbortController();
            
            singleProgressContainer.style.display = "none";
            batchProgressContainer.style.display = "block";
            btnAbortBatch.style.display = "block";
            processingTitle.textContent = "Processing Video Batch...";
            
            // Mark all items as pending
            selectedFiles.forEach((_, i) => {
                updateQueueItemStatus(i, "pending", "Pending");
            });
            
            switchResultState("processing");
            processNextBatchItem();
        }
    });

    function uploadSingleFile(file) {
        const formData = new FormData(extractForm);
        formData.set("video", file);
        formData.set("dry_run", document.getElementById("dry-run").checked);
        formData.set("minor_possible", document.getElementById("minor-possible").checked);
        formData.set("embed_metadata", document.getElementById("embed-metadata").checked);

        fetch("/api/extract", {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Server processing failed") });
            }
            return response.json();
        })
        .then(data => {
            renderResult(data);
            switchResultState("result");
        })
        .catch(err => {
            errorMessage.textContent = err.message;
            switchResultState("error");
        });
    }

    const STAGE_ORDER = [
        { code: "safety_check", text: "Initializing safety filters", pct: 10 },
        { code: "uploading_to_gemini", text: "Uploading video to Google Gemini File API", pct: 25 },
        { code: "processing_on_gemini", text: "Transcoding and processing on Gemini servers", pct: 45 },
        { code: "querying_model", text: "Analyzing clothing details & extracting attributes", pct: 70 },
        { code: "generating_embeddings", text: "Generating semantic outfit embeddings", pct: 80 },
        { code: "warming_constellation_cache", text: "Updating Outfit Constellation cluster mapping", pct: 90 },
        { code: "writing_video_metadata", text: "Embedding AI findings into source video file", pct: 95 }
    ];

    function renderChecklist(activeCode) {
        if (!processingStepsChecklist) return;
        
        let activeIndex = STAGE_ORDER.findIndex(s => s.code === activeCode);
        if (activeCode === "success") {
            activeIndex = STAGE_ORDER.length; // All completed
            if (singleProgressBarFill && singleProgressPercent) {
                singleProgressBarFill.style.width = "100%";
                singleProgressPercent.textContent = "100%";
            }
        } else if (activeIndex === -1) {
            activeIndex = 0;
        }

        processingStepsChecklist.innerHTML = "";
        STAGE_ORDER.forEach((stage, idx) => {
            const stepDiv = document.createElement("div");
            stepDiv.className = "processing-step";
            
            let iconHtml = "";
            if (idx < activeIndex) {
                stepDiv.classList.add("completed");
                iconHtml = `<i data-lucide="check-circle"></i>`;
            } else if (idx === activeIndex) {
                stepDiv.classList.add("active");
                iconHtml = `<i data-lucide="loader" class="spin"></i>`;
                
                // Update progress bar
                if (singleProgressBarFill && singleProgressPercent) {
                    singleProgressBarFill.style.width = `${stage.pct}%`;
                    singleProgressPercent.textContent = `${stage.pct}%`;
                }
            } else {
                stepDiv.classList.add("pending");
                iconHtml = `<i data-lucide="circle"></i>`;
            }
            
            stepDiv.innerHTML = `${iconHtml}<span>${stage.text}</span>`;
            processingStepsChecklist.appendChild(stepDiv);
        });

        lucide.createIcons();
    }

    function pollRunStatus(runId, onSuccess, onFailure) {
        const pollInterval = setInterval(() => {
            fetch(`/api/runs/${runId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error("Failed to check status");
                }
                return response.json();
            })
            .then(data => {
                if (data.status_detail) {
                    renderChecklist(data.status_detail);
                    const activeStage = STAGE_ORDER.find(s => s.code === data.status_detail);
                    if (activeStage) {
                        processingDetail.textContent = `${activeStage.text}. Please do not close this window.`;
                    }
                }
                
                if (data.status === "processing") {
                    return;
                }
                
                clearInterval(pollInterval);
                activePollInterval = null;
                
                if (data.status === "failed") {
                    renderChecklist("failed");
                    onFailure(new Error(data.error || "Processing failed."));
                } else if (data.status === "dry_run") {
                    renderChecklist("success");
                    // Clean up dry run from database history
                    fetch(`/api/runs/${runId}`, { method: "DELETE" })
                    .catch(err => console.error("Failed to delete dry run:", err));
                    
                    let resultData = data;
                    if (data.raw_json) {
                        try {
                            resultData = JSON.parse(data.raw_json);
                        } catch (e) {}
                    }
                    onSuccess(resultData);
                } else {
                    renderChecklist("success");
                    let resultData = data;
                    if (data.raw_json) {
                        try {
                            resultData = JSON.parse(data.raw_json);
                            resultData.db_id = runId;
                        } catch (e) {}
                    }
                    onSuccess(resultData);
                }
            })
            .catch(err => {
                clearInterval(pollInterval);
                activePollInterval = null;
                onFailure(err);
            });
        }, 2000);
        
        return pollInterval;
    }

    function uploadSingleFile(file) {
        renderChecklist("safety_check");
        const formData = new FormData(extractForm);
        formData.set("video", file);
        formData.set("dry_run", document.getElementById("dry-run").checked);
        formData.set("minor_possible", document.getElementById("minor-possible").checked);
        formData.set("embed_metadata", document.getElementById("embed-metadata").checked);

        if (activePollInterval) {
            clearInterval(activePollInterval);
            activePollInterval = null;
        }

        fetch("/api/extract", {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Server processing failed") });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === "processing") {
                activePollInterval = pollRunStatus(
                    data.run_id,
                    (result) => {
                        renderResult(result);
                        switchResultState("result");
                    },
                    (err) => {
                        errorMessage.textContent = err.message;
                        switchResultState("error");
                    }
                );
            } else {
                renderResult(data);
                switchResultState("result");
            }
        })
        .catch(err => {
            errorMessage.textContent = err.message;
            switchResultState("error");
        });
    }

    function processNextBatchItem() {
        if (!isBatchActive) return;
        
        if (currentBatchIndex >= selectedFiles.length) {
            showToast(`Batch extraction completed successfully! Processed ${selectedFiles.length} files.`, "success");
            isBatchActive = false;
            switchResultState("idle");
            
            selectedFiles = [];
            fileNameDisplay.textContent = "";
            batchQueueContainer.style.display = "none";
            btnSubmit.disabled = true;
            return;
        }

        const file = selectedFiles[currentBatchIndex];
        const total = selectedFiles.length;
        const progressPct = Math.round((currentBatchIndex / total) * 100);
        
        batchProgressStatus.textContent = `Processing file ${currentBatchIndex + 1} of ${total}`;
        batchProgressPercent.textContent = `${progressPct}%`;
        batchProgressBarFill.style.width = `${progressPct}%`;
        processingDetail.textContent = `Extracting attributes for "${file.name}"...`;
        
        renderChecklist("safety_check");
        updateQueueItemStatus(currentBatchIndex, "processing", "Processing");

        const formData = new FormData(extractForm);
        formData.set("video", file);
        formData.set("dry_run", document.getElementById("dry-run").checked);
        formData.set("minor_possible", document.getElementById("minor-possible").checked);
        formData.set("embed_metadata", document.getElementById("embed-metadata").checked);

        if (activePollInterval) {
            clearInterval(activePollInterval);
            activePollInterval = null;
        }

        fetch("/api/extract", {
            method: "POST",
            body: formData,
            signal: abortController ? abortController.signal : null
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Server processing failed") });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === "processing") {
                activePollInterval = pollRunStatus(
                    data.run_id,
                    (result) => {
                        updateQueueItemStatus(currentBatchIndex, "success", "Success");
                        renderResult(result);
                        proceedAfterBatchItem();
                    },
                    (err) => {
                        updateQueueItemStatus(currentBatchIndex, "failed", "Failed");
                        console.error(`Batch item failed: ${file.name}`, err);
                        proceedAfterBatchItem();
                    }
                );
            } else {
                updateQueueItemStatus(currentBatchIndex, "success", "Success");
                renderResult(data);
                proceedAfterBatchItem();
            }
        })
        .catch(err => {
            if (err.name === "AbortError") {
                return;
            }
            
            updateQueueItemStatus(currentBatchIndex, "failed", "Failed");
            console.error(`Batch item failed: ${file.name}`, err);
            
            proceedAfterBatchItem();
        });

        function proceedAfterBatchItem() {
            currentBatchIndex++;
            
            if (isBatchActive && currentBatchIndex < total) {
                const delaySec = parseInt(batchDelayInput.value) || 10;
                let remaining = delaySec;
                
                const countdownInterval = setInterval(() => {
                    if (!isBatchActive) {
                        clearInterval(countdownInterval);
                        return;
                    }
                    remaining--;
                    if (remaining <= 0) {
                        clearInterval(countdownInterval);
                        processNextBatchItem();
                    } else {
                        processingDetail.textContent = `Waiting ${remaining}s before starting next file...`;
                    }
                }, 1000);
                
                processingDetail.textContent = `Waiting ${remaining}s before starting next file...`;
            } else {
                processNextBatchItem();
            }
        }
    }

    if (btnAbortBatch) {
        btnAbortBatch.addEventListener("click", async () => {
            if (!await showConfirm("Are you sure you want to abort the current batch extraction queue? Unprocessed files will be skipped.", true)) return;
            
            isBatchActive = false;
            if (activePollInterval) {
                clearInterval(activePollInterval);
                activePollInterval = null;
            }
            if (abortController) {
                abortController.abort();
            }
            
            for (let i = currentBatchIndex; i < selectedFiles.length; i++) {
                updateQueueItemStatus(i, "aborted", "Aborted");
            }
            
            showToast("Batch extraction aborted by user.", "warning");
            switchResultState("idle");
            
            selectedFiles = [];
            fileNameDisplay.textContent = "";
            batchQueueContainer.style.display = "none";
            btnSubmit.disabled = true;
        });
    }

    // --- Render Extraction Result ---
    function renderResult(data) {
        const chunk = data.chunks ? data.chunks[0] : null;
        const platformMeta = chunk ? chunk.platform_metadata : null;
        const platformName = platformMeta ? platformMeta.platform : (data.platform_name || null);
        const platformHandle = platformMeta ? platformMeta.handle : (data.platform_handle || null);
        
        const handleBadge = platformHandle 
            ? `<span class="attr-badge topwear" style="margin-left: 0.5rem; font-size: 0.65rem; padding: 0.15rem 0.4rem; vertical-align: middle;">${platformName || 'Watermark'}: ${platformHandle}</span>` 
            : '';
        
        const videoLink = data.db_id
            ? `<button class="btn-video-link" data-run-id="${data.db_id}" data-video-name="${data.source_video}" style="margin-left: 0.5rem; vertical-align: middle;"><i data-lucide="play-circle"></i> Watch Video</button>
               <a class="btn-video-link" href="/api/runs/${data.db_id}/video-with-metadata" download style="margin-left: 0.25rem; vertical-align: middle;"><i data-lucide="download"></i> Download</a>`
            : '';
        resultTitle.innerHTML = `<span style="vertical-align: middle;">${data.source_video}</span>${handleBadge}${videoLink}`;
        
        // 1. Status badge
        const status = chunk ? chunk.status : "ok";
        resultStatus.className = `status-badge ${status === 'ok' ? 'success' : 'warning'}`;
        resultStatus.textContent = status;

        // 2. People cards
        resultPeopleContainer.innerHTML = "";
        const peopleList = chunk ? chunk.people : [];
        if (peopleList.length === 0) {
            resultPeopleContainer.innerHTML = `
                <div class="people-card">
                    <h4>No Person Detected</h4>
                    <p style="font-size: 0.75rem; color: rgba(255,255,255,0.4)">The model detected no clothing or hair attributes in the video chunk.</p>
                </div>`;
        } else {
            peopleList.forEach(person => {
                resultPeopleContainer.appendChild(createPersonCard(person, false, data.db_id));
            });
        }

        // 3. Metadata
        const meta = data.run_metadata || {};
        resultMetadata.innerHTML = `
            <div class="meta-item"><span>Model:</span> <span>${data.model}</span></div>
            <div class="meta-item"><span>Status:</span> <span>${status}</span></div>
            <div class="meta-item"><span>Input Tokens:</span> <span>${meta.total_input_tokens || 0}</span></div>
            <div class="meta-item"><span>Output Tokens:</span> <span>${meta.total_output_tokens || 0}</span></div>
            <div class="meta-item"><span>Estimated Cost:</span> <span>$${(meta.estimated_cost_usd || 0).toFixed(4)}</span></div>
            <div class="meta-item"><span>Date:</span> <span>${new Date().toLocaleTimeString()}</span></div>
        `;
    }

    function createPersonCard(person, isEditable = false, runId = null) {
        const card = document.createElement("div");
        card.className = "people-card";

        const header = document.createElement("div");
        header.className = "people-card-header";

        const titleGroup = document.createElement("div");
        titleGroup.style.display = "flex";
        titleGroup.style.alignItems = "center";
        titleGroup.style.gap = "0.5rem";
        titleGroup.style.flexWrap = "wrap";

        const title = document.createElement("h4");
        title.textContent = person.person_label;
        titleGroup.appendChild(title);

        // Add video link button if runId is available
        if (runId) {
            const videoLink = document.createElement("button");
            videoLink.className = "btn-video-link";
            videoLink.setAttribute("data-run-id", runId);
            videoLink.setAttribute("data-video-name", person.person_label);
            videoLink.innerHTML = `<i data-lucide="play-circle"></i> Watch Video`;
            titleGroup.appendChild(videoLink);
        }

        header.appendChild(titleGroup);

        if (isEditable && person.person_id) {
            const editBtn = document.createElement("button");
            editBtn.className = "btn-edit-person";
            editBtn.innerHTML = `<i data-lucide="edit-3"></i> Edit`;
            header.appendChild(editBtn);

            editBtn.addEventListener("click", () => {
                toggleEditPersonCard(card, person);
            });
        }
        card.appendChild(header);

        const rows = document.createElement("div");
        rows.className = "attribute-rows";

        // 1. Hair
        const hair = person.hair || {};
        const hairParts = [];
        if (hair.color) hairParts.push(hair.color);
        if (hair.texture) hairParts.push(hair.texture);
        if (hair.length) hairParts.push(hair.length);
        if (hair.style) hairParts.push(hair.style);
        
        if (hairParts.length > 0) {
            rows.appendChild(createBadge("hair", `Hair: ${hairParts.join(" · ")}`));
        } else {
            if (person.hair_color) {
                rows.appendChild(createBadge("hair", `Hair: ${person.hair_color}`));
            } else {
                rows.appendChild(createBadge("null-badge", "Hair: Not visible"));
            }
        }

        // Helper to format garment sentence
        function formatGarmentMain(g, defaultCategory) {
            const parts = [];
            if (g.color) parts.push(g.color);
            if (g.fit) parts.push(g.fit);
            if (g.fabric) {
                const fab = g.fabric.toLowerCase().trim();
                const typ = (g.type || "").toLowerCase().trim();
                if (!typ.includes(fab)) {
                    parts.push(g.fabric);
                }
            }
            if (g.type) {
                parts.push(g.type);
            } else {
                parts.push(defaultCategory);
            }
            return parts.join(" ");
        }

        // 2. Topwear
        const top = person.top || {};
        if (top.type || top.color) {
            let topText = formatGarmentMain(top, "topwear");
            const topExtras = [];
            if (top.neckline) topExtras.push(top.neckline);
            if (top.sleeve_length) topExtras.push(top.sleeve_length);
            if (top.pattern && top.pattern !== "solid") topExtras.push(`${top.pattern} pattern`);
            
            if (topExtras.length > 0) {
                topText += ` (${topExtras.join(", ")})`;
            }
            rows.appendChild(createBadge("topwear", `Top: ${topText}`));
            
            // Details pills
            if (top.details && top.details.length > 0) {
                top.details.forEach(d => {
                    rows.appendChild(createBadge("details-badge", d));
                });
            }
        } else {
            rows.appendChild(createBadge("null-badge", "Topwear: Not visible"));
        }

        // 3. Bottomwear
        const bottom = person.bottom || {};
        if (bottom.type || bottom.color) {
            let botText = formatGarmentMain(bottom, "bottomwear");
            const botExtras = [];
            if (bottom.garment_length) botExtras.push(bottom.garment_length);
            if (bottom.pattern && bottom.pattern !== "solid") botExtras.push(`${bottom.pattern} pattern`);
            
            if (botExtras.length > 0) {
                botText += ` (${botExtras.join(", ")})`;
            }
            rows.appendChild(createBadge("bottomwear", `Bottom: ${botText}`));
            
            // Details pills
            if (bottom.details && bottom.details.length > 0) {
                bottom.details.forEach(d => {
                    rows.appendChild(createBadge("details-badge", d));
                });
            }
        } else {
            rows.appendChild(createBadge("null-badge", "Bottomwear: Not visible"));
        }

        card.appendChild(rows);
        return card;
    }

    function toggleEditPersonCard(card, person) {
        const header = card.querySelector(".people-card-header");
        if (header) {
            const editBtn = header.querySelector(".btn-edit-person");
            if (editBtn) editBtn.style.display = "none";
        }
        
        const rows = card.querySelector(".attribute-rows");
        if (rows) rows.style.display = "none";
        
        const formContainer = document.createElement("div");
        formContainer.className = "edit-form-container";
        
        const hair = person.hair || {};
        const top = person.top || {};
        const bottom = person.bottom || {};
        
        formContainer.innerHTML = `
            <div class="edit-form-section">
                <h5>Hair Attributes</h5>
                <div class="edit-form-grid">
                    <div class="edit-field"><label>Color</label><input type="text" name="hair_color" value="${hair.color || ''}"></div>
                    <div class="edit-field"><label>Texture</label><input type="text" name="hair_texture" value="${hair.texture || ''}"></div>
                    <div class="edit-field"><label>Length</label><input type="text" name="hair_length" value="${hair.length || ''}"></div>
                    <div class="edit-field"><label>Style</label><input type="text" name="hair_style" value="${hair.style || ''}"></div>
                </div>
            </div>
            <div class="edit-form-section">
                <h5>Topwear Attributes</h5>
                <div class="edit-form-grid">
                    <div class="edit-field"><label>Type</label><input type="text" name="top_type" value="${top.type || ''}"></div>
                    <div class="edit-field"><label>Color</label><input type="text" name="top_color" value="${top.color || ''}"></div>
                    <div class="edit-field"><label>Fit</label><input type="text" name="top_fit" value="${top.fit || ''}"></div>
                    <div class="edit-field"><label>Fabric</label><input type="text" name="top_fabric" value="${top.fabric || ''}"></div>
                    <div class="edit-field"><label>Pattern</label><input type="text" name="top_pattern" value="${top.pattern || ''}"></div>
                    <div class="edit-field"><label>Neckline</label><input type="text" name="top_neckline" value="${top.neckline || ''}"></div>
                    <div class="edit-field"><label>Sleeve Length</label><input type="text" name="top_sleeve_length" value="${top.sleeve_length || ''}"></div>
                    <div class="edit-field"><label>Details (comma-separated)</label><input type="text" name="top_details" value="${(top.details || []).join(', ')}"></div>
                </div>
            </div>
            <div class="edit-form-section">
                <h5>Bottomwear Attributes</h5>
                <div class="edit-form-grid">
                    <div class="edit-field"><label>Type</label><input type="text" name="bottom_type" value="${bottom.type || ''}"></div>
                    <div class="edit-field"><label>Color</label><input type="text" name="bottom_color" value="${bottom.color || ''}"></div>
                    <div class="edit-field"><label>Fit</label><input type="text" name="bottom_fit" value="${bottom.fit || ''}"></div>
                    <div class="edit-field"><label>Fabric</label><input type="text" name="bottom_fabric" value="${bottom.fabric || ''}"></div>
                    <div class="edit-field"><label>Pattern</label><input type="text" name="bottom_pattern" value="${bottom.pattern || ''}"></div>
                    <div class="edit-field"><label>Garment Length</label><input type="text" name="bottom_garment_length" value="${bottom.garment_length || ''}"></div>
                    <div class="edit-field"><label>Details (comma-separated)</label><input type="text" name="bottom_details" value="${(bottom.details || []).join(', ')}"></div>
                </div>
            </div>
            <div class="edit-actions">
                <button class="btn-secondary btn-cancel-edit">Cancel</button>
                <button class="btn-primary btn-save-edit">Save</button>
            </div>
        `;
        
        card.appendChild(formContainer);
        
        const cancelBtn = formContainer.querySelector(".btn-cancel-edit");
        cancelBtn.addEventListener("click", () => {
            formContainer.remove();
            if (header) {
                const editBtn = header.querySelector(".btn-edit-person");
                if (editBtn) editBtn.style.display = "inline-flex";
            }
            if (rows) rows.style.display = "flex";
        });
        
        const saveBtn = formContainer.querySelector(".btn-save-edit");
        saveBtn.addEventListener("click", () => {
            const getVal = (name) => formContainer.querySelector(`[name="${name}"]`).value.trim();
            const getDetailsList = (name) => {
                const val = getVal(name);
                return val ? val.split(",").map(s => s.trim()).filter(Boolean) : [];
            };
            
            const updatedData = {
                hair: {
                    color: getVal("hair_color") || null,
                    texture: getVal("hair_texture") || null,
                    length: getVal("hair_length") || null,
                    style: getVal("hair_style") || null
                },
                top: {
                    type: getVal("top_type") || null,
                    color: getVal("top_color") || null,
                    fit: getVal("top_fit") || null,
                    fabric: getVal("top_fabric") || null,
                    pattern: getVal("top_pattern") || null,
                    neckline: getVal("top_neckline") || null,
                    sleeve_length: getVal("top_sleeve_length") || null,
                    details: getDetailsList("top_details")
                },
                bottom: {
                    type: getVal("bottom_type") || null,
                    color: getVal("bottom_color") || null,
                    fit: getVal("bottom_fit") || null,
                    fabric: getVal("bottom_fabric") || null,
                    pattern: getVal("bottom_pattern") || null,
                    garment_length: getVal("bottom_garment_length") || null,
                    details: getDetailsList("bottom_details")
                }
            };
            
            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            
            fetch(`/api/people/${person.person_id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updatedData)
            })
            .then(res => res.json())
            .then(resData => {
                if (resData.success) {
                    showToast("Person attributes updated successfully!", "success");
                    
                    // Reload panel/modal
                    const activeTab = document.querySelector(".nav-tab.active");
                    if (activeTab && activeTab.id === "tab-history") {
                        const currentRunId = modalRunTitle.getAttribute("data-run-id");
                        if (currentRunId) {
                            showRunDetail(currentRunId);
                            loadHistory();
                        }
                    } else if (activeTab && activeTab.id === "tab-constellation") {
                        loadConstellation();
                        if (selectedPoint) {
                            showConstellationDetail(selectedPoint);
                        }
                    }
                } else {
                    showToast("Failed to save: " + resData.error, "error");
                    saveBtn.disabled = false;
                    saveBtn.textContent = "Save";
                }
            })
            .catch(err => {
                showToast("Network error: " + err.message, "error");
                saveBtn.disabled = false;
                saveBtn.textContent = "Save";
            });
        });
    }

    function createBadge(typeClass, text) {
        const badge = document.createElement("span");
        badge.className = `attr-badge ${typeClass}`;
        badge.textContent = text;
        return badge;
    }

    // --- History Operations ---
    function loadHistory() {
        fetch("/api/runs")
            .then(res => res.json())
            .then(data => {
                renderHistoryCards(data);
            })
            .catch(err => {
                console.error("Failed to load history:", err);
            });
    }

    if (btnRefreshHistory) {
        btnRefreshHistory.addEventListener("click", loadHistory);
    }

    function renderHistoryCards(runs) {
        historyGrid.innerHTML = "";
        if (runs.length === 0) {
            historyGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.4); padding: 3rem 1rem;">
                    No runs logged in database yet.
                </div>`;
            return;
        }

        runs.forEach(run => {
            const card = document.createElement("div");
            card.className = "history-run-card glass-card";
            card.setAttribute("data-id", run.id);
            
            // Format dates
            const dateObj = new Date(run.created_at + "Z"); // UTC from database
            const localDate = dateObj.toLocaleDateString() + " " + dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            const durationText = run.duration_sec ? `${run.duration_sec.toFixed(1)}s` : "0.0s";
            const costText = run.est_cost_usd ? `$${run.est_cost_usd.toFixed(4)}` : "$0.0000";

            const handleBadge = run.platform_handle 
                ? `<span class="attr-badge topwear" style="margin-left: 0.5rem; font-size: 0.65rem; padding: 0.15rem 0.4rem; vertical-align: middle;">${run.platform_name || 'Watermark'}: ${run.platform_handle}</span>` 
                : '';

            card.innerHTML = `
                <div class="run-card-header">
                    <div class="run-card-title" style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.25rem;">
                        <span style="vertical-align: middle;">${run.source_video}</span>
                        ${handleBadge}
                    </div>
                    <div class="run-card-date">${localDate}</div>
                </div>
                <div class="run-card-stats">
                    <div class="stat-box">
                        <span class="stat-label">People</span>
                        <span class="stat-val">${run.people_count || 0}</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">Duration</span>
                        <span class="stat-val">${durationText}</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">Cost</span>
                        <span class="stat-val">${costText}</span>
                    </div>
                </div>
                <div class="run-card-footer">
                    <span class="run-card-model">${run.model}</span>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button class="btn-video-link" data-run-id="${run.id}" data-video-name="${run.source_video}">
                            <i data-lucide="play-circle"></i> Video
                        </button>
                        <a class="btn-video-link" href="/api/runs/${run.id}/video-with-metadata" download>
                            <i data-lucide="download"></i> Download
                        </a>
                        <button class="btn-delete-card" data-id="${run.id}">Delete</button>
                    </div>
                </div>
            `;

            // Click card to show details, unless delete or video link is clicked
            card.addEventListener("click", (e) => {
                if (e.target.closest(".btn-delete-card")) {
                    e.stopPropagation();
                    deleteRun(run.id);
                } else if (e.target.closest(".btn-video-link, .btn-video-link-sm")) {
                    e.stopPropagation();
                } else {
                    showRunDetail(run.id);
                }
            });

            historyGrid.appendChild(card);
        });

        // Initialize newly generated Lucide icons inside cards
        lucide.createIcons();
    }

    async function deleteRun(runId) {
        if (!await showConfirm("Are you sure you want to delete this run from database history?", true)) return;

        fetch(`/api/runs/${runId}`, {
            method: "DELETE"
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                loadHistory();
            } else {
                showToast("Failed to delete run: " + data.error, "error");
            }
        })
        .catch(err => {
            showToast("Network error: " + err.message, "error");
        });
    }

    function showRunDetail(runId) {
        fetch(`/api/runs/${runId}`)
            .then(res => res.json())
            .then(run => {
                const handleBadge = run.platform_handle 
                    ? `<span class="attr-badge topwear" style="margin-left: 0.5rem; font-size: 0.65rem; padding: 0.15rem 0.4rem; vertical-align: middle;">${run.platform_name || 'Watermark'}: ${run.platform_handle}</span>` 
                    : '';
                const videoBtn = `<button class="btn-video-link" data-run-id="${runId}" data-video-name="${run.source_video}" style="margin-left: 0.5rem; vertical-align: middle;"><i data-lucide="play-circle"></i> Watch Video</button>`;
                modalRunTitle.innerHTML = `<span style="vertical-align: middle;">${run.source_video}</span>${handleBadge}${videoBtn}`;
                modalRunTitle.setAttribute("data-run-id", runId);
                modalPeopleContainer.innerHTML = "";
                
                if (run.people.length === 0) {
                    modalPeopleContainer.innerHTML = `
                        <div class="people-card">
                            <h4>No Person Detected</h4>
                            <p style="font-size: 0.75rem; color: rgba(255,255,255,0.4)">The model detected no clothing or hair attributes in the video chunk.</p>
                        </div>`;
                } else {
                    run.people.forEach(person => {
                        modalPeopleContainer.appendChild(createPersonCard(person, true, runId));
                    });
                }

                const dateObj = new Date(run.created_at + "Z");
                const localDate = dateObj.toLocaleDateString() + " " + dateObj.toLocaleTimeString();

                modalMetadata.innerHTML = `
                    <div class="meta-item"><span>Model:</span> <span>${run.model}</span></div>
                    <div class="meta-item"><span>Status:</span> <span>${run.status}</span></div>
                    <div class="meta-item"><span>Input Tokens:</span> <span>${run.input_tokens || 0}</span></div>
                    <div class="meta-item"><span>Output Tokens:</span> <span>${run.output_tokens || 0}</span></div>
                    <div class="meta-item"><span>Estimated Cost:</span> <span>$${(run.est_cost_usd || 0).toFixed(4)}</span></div>
                    <div class="meta-item"><span>Analyzed At:</span> <span>${localDate}</span></div>
                `;

                historyDetailModal.classList.add("active");
                lucide.createIcons();
            })
            .catch(err => {
                showToast("Failed to load run detail: " + err.message, "error");
            });
    }

    // Modal Close
    if (btnCloseModal) {
        btnCloseModal.addEventListener("click", () => {
            historyDetailModal.classList.remove("active");
        });
    }

    // Click outside modal content to close
    window.addEventListener("click", (e) => {
        if (e.target === historyDetailModal) {
            historyDetailModal.classList.remove("active");
        }
    });

    // Helper Formats
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // --- Outfit Constellation Map Logic ---
    const filterBtns = document.querySelectorAll(".filter-toggle-btn");
    const canvas = document.getElementById("constellation-canvas");
    const constellationTooltip = document.getElementById("constellation-tooltip");
    const constellationDetailPanel = document.getElementById("constellation-detail-panel");
    const btnCloseConstellationPanel = document.getElementById("btn-close-constellation-panel");
    const btnReembedAll = document.getElementById("btn-reembed-all");
    const constellationPanelVideo = document.getElementById("constellation-panel-video");
    const constellationPanelLabel = document.getElementById("constellation-panel-label");
    const constellationPanelAttributes = document.getElementById("constellation-panel-attributes");
    const constellationPanelSimilar = document.getElementById("constellation-panel-similar");

    let currentMode = "full";
    let points = [];
    let ctx = null;
    if (canvas) {
        ctx = canvas.getContext("2d");
    }

    let zoom = 1.0;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let hoveredPoint = null;
    let selectedPoint = null;
    let mdsScale = 300;

    const COLOR_MAP = {
        "red": "#ef4444",
        "pink": "#ec4899",
        "blue": "#3b82f6",
        "light blue": "#93c5fd",
        "sky blue": "#bae6fd",
        "navy": "#1e3a8a",
        "royal blue": "#1d4ed8",
        "green": "#10b981",
        "dark green": "#064e3b",
        "light green": "#86efac",
        "forest green": "#14532d",
        "olive": "#84cc16",
        "sage": "#a7f3d0",
        "mint": "#6ee7b7",
        "amber": "#f59e0b",
        "yellow": "#eab308",
        "orange": "#f97316",
        "white": "#ffffff",
        "ivory": "#fffde7",
        "cream": "#fef3c7",
        "beige": "#f5f5dc",
        "khaki": "#f0e68c",
        "tan": "#d2b48c",
        "brown": "#78350f",
        "maroon": "#800000",
        "burgundy": "#800020",
        "purple": "#a855f7",
        "violet": "#8b5cf6",
        "lavender": "#e9d5ff",
        "magenta": "#d946ef",
        "coral": "#f87171",
        "peach": "#ffedd5",
        "rust": "#b45309",
        "teal": "#0d9488",
        "turquoise": "#2dd4bf",
        "denim": "#4b5563",
        "gold": "#fbbf24",
        "silver": "#cbd5e1",
        "black": "#1e293b",
        "dark": "#0f172a",
        "gray": "#6b7280",
        "grey": "#6b7280",
        "charcoal": "#374151"
    };

    function getDominantColorHex(colorName) {
        if (!colorName) return "#6b7280";
        const name = colorName.toLowerCase().trim();
        if (COLOR_MAP[name]) return COLOR_MAP[name];
        
        // Try multi-word composite detection first
        for (const [key, value] of Object.entries(COLOR_MAP)) {
            if (key.includes(" ") && name.includes(key)) return value;
        }
        // Fall back to single-word detection
        for (const [key, value] of Object.entries(COLOR_MAP)) {
            if (!key.includes(" ") && name.includes(key)) return value;
        }
        return "#6b7280";
    }

    // Constellation Guide Hint Logic
    function checkShowHint() {
        if (canvas && constellationHint) {
            const hintSeen = localStorage.getItem("wovely-constellation-hint-seen");
            if (!hintSeen) {
                constellationHint.style.display = "flex";
                // Auto-fade after 8 seconds
                setTimeout(hideHint, 8000);
            } else {
                constellationHint.style.display = "none";
            }
        }
    }

    function hideHint() {
        if (constellationHint && constellationHint.style.display !== "none") {
            constellationHint.classList.add("fade-out");
            constellationHint.addEventListener("transitionend", () => {
                constellationHint.style.display = "none";
                constellationHint.classList.remove("fade-out");
            }, { once: true });
            localStorage.setItem("wovely-constellation-hint-seen", "true");
        }
    }

    if (btnCloseHint) {
        btnCloseHint.addEventListener("click", (e) => {
            e.stopPropagation();
            hideHint();
        });
    }

    function loadConstellation() {
        if (!canvas) return;
        
        constellationDetailPanel.classList.remove("active");
        selectedPoint = null;
        hoveredPoint = null;
        listHoveredPoint = null;
        constellationTooltip.style.display = "none";
        
        checkShowHint();
        
        fetch(`/api/constellation?mode=${currentMode}`)
            .then(res => res.json())
            .then(data => {
                points = data;
                
                if (points.length > 1) {
                    let maxVal = 0.01;
                    points.forEach(p => {
                        maxVal = Math.max(maxVal, Math.abs(p.x), Math.abs(p.y));
                    });
                    const rect = canvas.parentElement.getBoundingClientRect();
                    canvas.width = rect.width;
                    canvas.height = rect.height;
                    mdsScale = (Math.min(canvas.width, canvas.height) * 0.35) / maxVal;
                } else {
                    mdsScale = 150;
                }
                
                zoom = 1.0;
                panX = 0;
                panY = 0;
                
                resizeCanvas();
            })
            .catch(err => {
                console.error("Failed to load constellation data:", err);
            });
    }

    function resizeCanvas() {
        if (!canvas) return;
        const rect = canvas.parentElement.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = rect.width + "px";
        canvas.style.height = rect.height + "px";
        
        ctx.resetTransform();
        ctx.scale(dpr, dpr);
        
        drawConstellation();
    }

    function hexToRgba(hex, alpha) {
        if (!hex || !hex.startsWith("#")) return hex;
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function drawConstellation() {
        if (!ctx || !canvas) return;
        const rect = canvas.getBoundingClientRect();
        
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.restore();

        if (points.length === 0) {
            ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
            ctx.font = "14px Geist, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No runs or analyzed outfits in history database.", rect.width / 2, rect.height / 2);
            ctx.fillText("Upload and analyze a video to populate coordinates.", rect.width / 2, rect.height / 2 + 20);
            return;
        }

        ctx.save();
        ctx.translate(rect.width / 2 + panX, rect.height / 2 + panY);
        ctx.scale(zoom, zoom);

        // 1. Draw connecting lines between points whose distance is close (< 0.25 under raw MDS scale)
        for (let i = 0; i < points.length; i++) {
            if (!pointMatchesSearch(points[i])) continue;
            for (let j = i + 1; j < points.length; j++) {
                if (!pointMatchesSearch(points[j])) continue;
                const dx = points[i].x - points[j].x;
                const dy = points[i].y - points[j].y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (dist < 0.25) {
                    let opacity = 0.05;
                    if (listHoveredPoint) {
                        const isMainConnection = (
                            (points[i] === selectedPoint && points[j] === listHoveredPoint) ||
                            (points[j] === selectedPoint && points[i] === listHoveredPoint)
                        );
                        opacity = isMainConnection ? 0.6 : 0.005;
                    }
                    
                    ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
                    ctx.lineWidth = (listHoveredPoint && ((points[i] === selectedPoint && points[j] === listHoveredPoint) || (points[j] === selectedPoint && points[i] === listHoveredPoint))) ? 2 / zoom : 1 / zoom;
                    ctx.beginPath();
                    ctx.moveTo(points[i].x * mdsScale, points[i].y * mdsScale);
                    ctx.lineTo(points[j].x * mdsScale, points[j].y * mdsScale);
                    ctx.stroke();
                }
            }
        }

        // 1.5 Draw highlighted direct connection line if listHoveredPoint is active
        if (listHoveredPoint && selectedPoint && pointMatchesSearch(listHoveredPoint) && pointMatchesSearch(selectedPoint)) {
            ctx.save();
            const color = getDominantColorHex(listHoveredPoint.dominant_color);
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5 / zoom;
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
            ctx.setLineDash([4 / zoom, 4 / zoom]);
            
            ctx.beginPath();
            ctx.moveTo(selectedPoint.x * mdsScale, selectedPoint.y * mdsScale);
            ctx.lineTo(listHoveredPoint.x * mdsScale, listHoveredPoint.y * mdsScale);
            ctx.stroke();
            ctx.restore();
        }

        // 2. Draw dots
        points.forEach(p => {
            const px = p.x * mdsScale;
            const py = p.y * mdsScale;
            
            const matchesQuery = pointMatchesSearch(p);
            const isTarget = (hoveredPoint === p || selectedPoint === p || (listHoveredPoint && listHoveredPoint === p));
            const color = getDominantColorHex(p.dominant_color);
            
            let opacity = 1.0;
            if (!matchesQuery) {
                opacity = 0.1;
            } else if (listHoveredPoint) {
                if (p !== selectedPoint && p !== listHoveredPoint) {
                    opacity = 0.15;
                }
            }
            
            const fillColor = (opacity < 1.0) ? hexToRgba(color, opacity) : color;
            
            ctx.shadowColor = color;
            ctx.shadowBlur = (isTarget && opacity > 0.5) ? 15 : (opacity > 0.5 && matchesQuery ? 6 : 0);
            
            ctx.fillStyle = fillColor;
            ctx.beginPath();
            const radius = isTarget ? 8 : 5;
            ctx.arc(px, py, radius, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.shadowBlur = 0;
            
            let strokeColor = (selectedPoint === p) ? "#ffffff" : "rgba(255, 255, 255, 0.4)";
            if (opacity < 1.0) {
                strokeColor = (selectedPoint === p) ? `rgba(255, 255, 255, ${opacity})` : `rgba(255, 255, 255, ${0.4 * opacity})`;
            }
            
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = (selectedPoint === p) ? 2 / zoom : 1 / zoom;
            ctx.stroke();
        });

        ctx.restore();
    }

    function getMousePosTransformed(e) {
        if (!canvas) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const tx = (mouseX - rect.width / 2 - panX) / zoom;
        const ty = (mouseY - rect.height / 2 - panY) / zoom;
        return { x: tx, y: ty };
    }

    function pointMatchesSearch(p) {
        if (!searchQuery) return true;
        
        const summaryText = (p.summary || "").toLowerCase();
        const videoText = (p.source_video || "").toLowerCase();
        const labelText = (p.person_label || "").toLowerCase();
        const colorText = (p.dominant_color || "").toLowerCase();
        const hairText = (p.hair_summary || "").toLowerCase();
        
        return (
            summaryText.includes(searchQuery) ||
            videoText.includes(searchQuery) ||
            labelText.includes(searchQuery) ||
            colorText.includes(searchQuery) ||
            hairText.includes(searchQuery)
        );
    }

    function checkHover(e) {
        if (!canvas || points.length === 0) return;
        const pos = getMousePosTransformed(e);
        let found = null;
        let minDist = 10 / zoom; // 10px hover radius
        
        points.forEach(p => {
            if (!pointMatchesSearch(p)) return;
            const px = p.x * mdsScale;
            const py = p.y * mdsScale;
            const dist = Math.sqrt((pos.x - px) ** 2 + (pos.y - py) ** 2);
            if (dist < minDist) {
                minDist = dist;
                found = p;
            }
        });
        
        if (found !== hoveredPoint) {
            hoveredPoint = found;
            drawConstellation();
            canvas.style.cursor = hoveredPoint ? "pointer" : "default";
            
            if (hoveredPoint) {
                const rect = canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                const fileShort = hoveredPoint.source_video.length > 25 ? hoveredPoint.source_video.slice(0, 22) + "..." : hoveredPoint.source_video;
                const labelShort = hoveredPoint.person_label;
                const colorLabel = getDominantColorHex(hoveredPoint.dominant_color);
                const colorDot = `<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:${colorLabel}; margin-right:4px;"></span>`;
                
                const formattedText = `
                    <div style="font-weight:600; font-family:var(--font-mono); margin-bottom:2px;">${fileShort} (${labelShort})</div>
                    <div style="color:rgba(255,255,255,0.7); font-size:0.7rem;">${colorDot}${hoveredPoint.summary}</div>
                    <div style="color:rgba(255,255,255,0.4); font-size:0.65rem; margin-top:2px;">Click to view similar outfits</div>
                `;
                
                constellationTooltip.innerHTML = formattedText;
                const tooltipWidth = 245;
                const tooltipHeight = 85;
                let tooltipX = mouseX + 15;
                let tooltipY = mouseY + 15;
                
                if (tooltipX + tooltipWidth > rect.width) {
                    tooltipX = mouseX - tooltipWidth - 15;
                }
                if (tooltipY + tooltipHeight > rect.height) {
                    tooltipY = mouseY - tooltipHeight - 15;
                }
                
                tooltipX = Math.max(10, tooltipX);
                tooltipY = Math.max(10, tooltipY);
                
                constellationTooltip.style.left = `${tooltipX}px`;
                constellationTooltip.style.top = `${tooltipY}px`;
                constellationTooltip.style.display = "block";
            } else {
                constellationTooltip.style.display = "none";
            }
        }
    }

    function showConstellationDetail(point) {
        const videoBtn = `<button class="btn-video-link" data-run-id="${point.run_id}" data-video-name="${point.source_video}" style="margin-top: 0.5rem;"><i data-lucide="play-circle"></i> Watch Video</button>`;
        constellationPanelVideo.innerHTML = `${point.source_video}${videoBtn}`;
        constellationPanelLabel.textContent = point.person_label;
        
        fetch(`/api/runs/${point.run_id}`)
            .then(res => res.json())
            .then(run => {
                const pData = run.people.find(p => p.person_label === point.person_label);
                if (pData) {
                    constellationPanelAttributes.innerHTML = "";
                    constellationPanelAttributes.appendChild(createPersonCard(pData, true, point.run_id));
                    lucide.createIcons();
                }
            });
            
        fetch(`/api/runs/${point.run_id}/similar?mode=${currentMode}&n=8`)
            .then(res => res.json())
            .then(data => {
                constellationPanelSimilar.innerHTML = "";
                if (data.length === 0) {
                    constellationPanelSimilar.innerHTML = `<div style="color:rgba(255,255,255,0.3); font-size:0.7rem; text-align:center; padding: 1rem;">No similar outfits in database.</div>`;
                    return;
                }
                
                data.forEach(match => {
                    const card = document.createElement("div");
                    card.className = "similar-match-item";
                    
                    const scorePct = Math.round(match.score * 100);
                    const topW = Math.round(match.top_score * 40);
                    const botW = Math.round(match.bottom_score * 35);
                    const hairW = Math.round(match.hair_score * 25);
                    
                    card.innerHTML = `
                        <div class="match-header">
                            <div style="display: flex; align-items: center; gap: 0.4rem; min-width: 0;">
                                <span class="match-video-name" title="${match.source_video}">${match.source_video}</span>
                                <button class="btn-video-link-sm" data-run-id="${match.run_id}" data-video-name="${match.source_video}" title="Watch Video"><i data-lucide="play-circle"></i></button>
                            </div>
                            <span class="match-pct">${scorePct}% match</span>
                        </div>
                        <div class="match-desc">${match.person_label} — ${match.outfit_summary}</div>
                        <div class="similarity-breakdown-container">
                            <div class="similarity-breakdown-bar">
                                <div class="breakdown-segment top" style="width: ${topW}%" title="Topwear similarity: ${Math.round(match.top_score*100)}%"></div>
                                <div class="breakdown-segment bottom" style="width: ${botW}%" title="Bottomwear similarity: ${Math.round(match.bottom_score*100)}%"></div>
                                <div class="breakdown-segment hair" style="width: ${hairW}%" title="Hair similarity: ${Math.round(match.hair_score*100)}%"></div>
                            </div>
                        </div>
                    `;
                    
                    // Bind hover events to locate and highlight matching node in canvas
                    const matchingPoint = points.find(p => p.run_id === match.run_id && p.person_label === match.person_label);
                    if (matchingPoint) {
                        card.addEventListener("mouseenter", () => {
                            listHoveredPoint = matchingPoint;
                            drawConstellation();
                        });
                        card.addEventListener("mouseleave", () => {
                            listHoveredPoint = null;
                            drawConstellation();
                        });
                    }
                    
                    constellationPanelSimilar.appendChild(card);
                });
                
                lucide.createIcons();
            });
            
        constellationDetailPanel.classList.add("active");
        drawConstellation();
    }

    let dragStartX = 0;
    let dragStartY = 0;

    if (canvas) {
        canvas.addEventListener("mousedown", (e) => {
            hideHint();
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
            dragStartX = e.clientX;
            dragStartY = e.clientY;
        });

        window.addEventListener("mousemove", (e) => {
            if (isDragging) {
                panX = e.clientX - startX;
                panY = e.clientY - startY;
                drawConstellation();
            } else {
                const rect = canvas.getBoundingClientRect();
                if (e.clientX >= rect.left && e.clientX <= rect.right &&
                    e.clientY >= rect.top && e.clientY <= rect.bottom) {
                    checkHover(e);
                }
            }
        });

        window.addEventListener("mouseup", () => {
            isDragging = false;
        });

        canvas.addEventListener("wheel", (e) => {
            hideHint();
            e.preventDefault();
            const zoomIntensity = 0.1;
            const mousePos = getMousePosTransformed(e);
            const newZoom = e.deltaY < 0 ? zoom * (1 + zoomIntensity) : zoom * (1 - zoomIntensity);
            
            if (newZoom >= 0.2 && newZoom <= 5.0) {
                panX -= mousePos.x * (newZoom - zoom);
                panY -= mousePos.y * (newZoom - zoom);
                zoom = newZoom;
                drawConstellation();
            }
        }, { passive: false });

        canvas.addEventListener("click", (e) => {
            const dist = Math.sqrt((e.clientX - dragStartX) ** 2 + (e.clientY - dragStartY) ** 2);
            if (dist < 5 && hoveredPoint) {
                selectedPoint = hoveredPoint;
                showConstellationDetail(selectedPoint);
            }
        });

        // Touch event handlers for mobile/tablet support
        let initialTouchDist = null;
        let initialZoom = 1.0;
        let touchStartPanX = 0;
        let touchStartPanY = 0;
        let isTouching = false;

        canvas.addEventListener("touchstart", (e) => {
            hideHint();
            if (e.touches.length === 1) {
                isTouching = true;
                const touch = e.touches[0];
                startX = touch.clientX - panX;
                startY = touch.clientY - panY;
                dragStartX = touch.clientX;
                dragStartY = touch.clientY;
                initialTouchDist = null;
            } else if (e.touches.length === 2) {
                isTouching = false;
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                initialTouchDist = Math.hypot(touch1.clientX - touch2.clientX, touch1.clientY - touch2.clientY);
                initialZoom = zoom;
                
                const midX = (touch1.clientX + touch2.clientX) / 2;
                const midY = (touch1.clientY + touch2.clientY) / 2;
                
                const rect = canvas.getBoundingClientRect();
                const cx = midX - rect.left;
                const cy = midY - rect.top;
                touchStartPanX = panX;
                touchStartPanY = panY;
            }
        }, { passive: true });

        canvas.addEventListener("touchmove", (e) => {
            if (e.touches.length === 1 && isTouching) {
                const touch = e.touches[0];
                panX = touch.clientX - startX;
                panY = touch.clientY - startY;
                drawConstellation();
            } else if (e.touches.length === 2 && initialTouchDist) {
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                const currentDist = Math.hypot(touch1.clientX - touch2.clientX, touch1.clientY - touch2.clientY);
                const factor = currentDist / initialTouchDist;
                
                let newZoom = initialZoom * factor;
                newZoom = Math.max(0.2, Math.min(5.0, newZoom));
                
                const rect = canvas.getBoundingClientRect();
                const midX = (touch1.clientX + touch2.clientX) / 2 - rect.left;
                const midY = (touch1.clientY + touch2.clientY) / 2 - rect.top;
                
                const tx = (midX - rect.width / 2 - touchStartPanX) / initialZoom;
                const ty = (midY - rect.height / 2 - touchStartPanY) / initialZoom;
                
                panX = midX - rect.width / 2 - tx * newZoom;
                panY = midY - rect.height / 2 - ty * newZoom;
                zoom = newZoom;
                drawConstellation();
            }
        }, { passive: true });

        canvas.addEventListener("touchend", (e) => {
            if (e.touches.length === 0) {
                if (isTouching) {
                    const dist = Math.hypot(e.changedTouches[0].clientX - dragStartX, e.changedTouches[0].clientY - dragStartY);
                    if (dist < 5) {
                        const rect = canvas.getBoundingClientRect();
                        const touchX = e.changedTouches[0].clientX - rect.left;
                        const touchY = e.changedTouches[0].clientY - rect.top;
                        
                        const fakeEvent = {
                            clientX: e.changedTouches[0].clientX,
                            clientY: e.changedTouches[0].clientY
                        };
                        checkHover(fakeEvent);
                        
                        if (hoveredPoint) {
                            selectedPoint = hoveredPoint;
                            showConstellationDetail(selectedPoint);
                        }
                    }
                }
                isTouching = false;
                initialTouchDist = null;
            }
        });

        window.addEventListener("resize", resizeCanvas);
    }

    filterBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            filterBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentMode = btn.getAttribute("data-mode");
            loadConstellation();
        });
    });

    if (btnCloseConstellationPanel) {
        btnCloseConstellationPanel.addEventListener("click", () => {
            constellationDetailPanel.classList.remove("active");
            selectedPoint = null;
            listHoveredPoint = null;
            drawConstellation();
        });
    }

    if (btnReembedAll) {
        btnReembedAll.addEventListener("click", async () => {
            if (!await showConfirm("Are you sure you want to regenerate and populate embeddings for all database runs? This calls the Google Embedding API for all runs.", false)) return;
            
            btnReembedAll.disabled = true;
            btnReembedAll.innerHTML = `<i data-lucide="refresh-cw" class="spin"></i> Re-embedding...`;
            lucide.createIcons();
            
            fetch("/api/runs")
                .then(res => res.json())
                .then(runs => {
                    const promises = runs.map(run => {
                        return fetch(`/api/runs/${run.id}/embed`, { method: "POST" });
                    });
                    return Promise.all(promises);
                })
                .then(() => {
                    showToast("Embeddings successfully generated for all run history!", "success");
                    loadConstellation();
                })
                .catch(err => {
                    showToast("Error backfilling embeddings: " + err.message, "error");
                })
                .finally(() => {
                    btnReembedAll.disabled = false;
                    btnReembedAll.innerHTML = `<i data-lucide="refresh-cw"></i> Re-embed All History`;
                    lucide.createIcons();
                });
        });
     }

    // --- Advanced Search Logic ---
    const includeRulesList = document.getElementById("include-rules-list");
    const excludeRulesList = document.getElementById("exclude-rules-list");
    const btnAddInclude = document.getElementById("btn-add-include");
    const btnAddExclude = document.getElementById("btn-add-exclude");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const btnRunSearch = document.getElementById("btn-run-search");
    const searchResultsGrid = document.getElementById("search-results-grid");
    const searchResultCount = document.getElementById("search-result-count");
    const searchModeBtns = document.querySelectorAll("[data-search-mode]");
    let searchMode = "AND";

    const categoryOptions = [
        { value: "person_label", text: "Person Label" },
        { value: "handle", text: "Platform Handle" },
        { value: "top_type", text: "Topwear Type" },
        { value: "top_color", text: "Topwear Color" },
        { value: "bottom_type", text: "Bottomwear Type" },
        { value: "bottom_color", text: "Bottomwear Color" },
        { value: "hair_color", text: "Hair Color" }
    ];

    function createSearchRuleRow() {
        const row = document.createElement("div");
        row.className = "search-rule-row";

        const select = document.createElement("select");
        select.className = "rule-category";
        categoryOptions.forEach(opt => {
            const option = document.createElement("option");
            option.value = opt.value;
            option.textContent = opt.text;
            select.appendChild(option);
        });

        const input = document.createElement("input");
        input.type = "text";
        input.className = "rule-value";
        input.placeholder = "Enter value...";

        const removeBtn = document.createElement("button");
        removeBtn.className = "btn-remove-rule";
        removeBtn.innerHTML = `<i data-lucide="x"></i>`;
        removeBtn.addEventListener("click", () => {
            row.remove();
            lucide.createIcons();
        });

        row.appendChild(select);
        row.appendChild(input);
        row.appendChild(removeBtn);
        
        lucide.createIcons();
        return row;
    }

    if (btnAddInclude) {
        btnAddInclude.addEventListener("click", () => {
            includeRulesList.appendChild(createSearchRuleRow());
        });
    }

    if (btnAddExclude) {
        btnAddExclude.addEventListener("click", () => {
            excludeRulesList.appendChild(createSearchRuleRow());
        });
    }

    if (btnClearSearch) {
        btnClearSearch.addEventListener("click", () => {
            includeRulesList.innerHTML = "";
            excludeRulesList.innerHTML = "";
            searchResultsGrid.innerHTML = "";
            searchResultCount.textContent = "";
        });
    }

    searchModeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            searchModeBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            searchMode = btn.getAttribute("data-search-mode");
        });
    });

    if (btnRunSearch) {
        btnRunSearch.addEventListener("click", () => {
            const includeRules = [];
            includeRulesList.querySelectorAll(".search-rule-row").forEach(row => {
                includeRules.push({
                    category: row.querySelector(".rule-category").value,
                    value: row.querySelector(".rule-value").value
                });
            });

            const excludeRules = [];
            excludeRulesList.querySelectorAll(".search-rule-row").forEach(row => {
                excludeRules.push({
                    category: row.querySelector(".rule-category").value,
                    value: row.querySelector(".rule-value").value
                });
            });

            if (includeRules.length === 0 && excludeRules.length === 0) {
                showToast("Please add at least one search rule.", "warning");
                return;
            }

            btnRunSearch.disabled = true;
            btnRunSearch.innerHTML = `<i data-lucide="loader" class="spin" style="width: 16px; height: 16px; margin-right: 0.3rem;"></i> Searching...`;
            lucide.createIcons();

            fetch("/api/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    include: includeRules,
                    exclude: excludeRules,
                    mode: searchMode
                })
            })
            .then(res => res.json())
            .then(data => {
                renderSearchResults(data);
            })
            .catch(err => {
                showToast("Search failed: " + err.message, "error");
            })
            .finally(() => {
                btnRunSearch.disabled = false;
                btnRunSearch.innerHTML = `<i data-lucide="search" style="width: 16px; height: 16px; margin-right: 0.3rem;"></i> Search Database`;
                lucide.createIcons();
            });
        });
    }

    function renderSearchResults(results) {
        searchResultsGrid.innerHTML = "";
        searchResultCount.textContent = `${results.length} match(es) found`;

        if (results.length === 0) {
            searchResultsGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.4); padding: 3rem 1rem;">
                    No outfits match your query.
                </div>`;
            return;
        }

        results.forEach(person => {
            const card = document.createElement("div");
            card.className = "search-result-card glass-card";
            
            const handleBadge = person.platform_handle 
                ? `<span class="attr-badge topwear" style="font-size: 0.65rem; padding: 0.15rem 0.4rem;">${person.platform_name || 'Watermark'}: ${person.platform_handle}</span>` 
                : '';

            const videoBtn = `<button class="btn-video-link" data-run-id="${person.run_id}" data-video-name="${person.source_video}"><i data-lucide="play-circle"></i> Video</button>`;
            
            card.innerHTML = `
                <div class="run-card-header">
                    <div class="run-card-title" style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.25rem;">
                        <span style="vertical-align: middle;">${person.source_video}</span>
                        ${handleBadge}
                    </div>
                    ${videoBtn}
                </div>
                <div id="search-card-attrs-${person.person_id}"></div>
            `;
            
            searchResultsGrid.appendChild(card);
            
            // Render attributes using existing logic
            const attrsContainer = card.querySelector(`#search-card-attrs-${person.person_id}`);
            const personCardElement = createPersonCard(person, false, person.run_id);
            personCardElement.style.padding = "0";
            personCardElement.style.border = "none";
            personCardElement.style.background = "transparent";
            attrsContainer.appendChild(personCardElement);
        });

        lucide.createIcons();
    }
});
