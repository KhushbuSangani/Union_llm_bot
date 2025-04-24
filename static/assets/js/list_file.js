class FileSelectionUI {
    constructor(files, file_length, displayLLMFilesUrl, pagination) {
        this.files = Array.isArray(files) ? files : [];
        this.selectedFiles = new Set(JSON.parse(localStorage.getItem("selectedFiles")) || []);
        this.selectedCount = Math.min(10, file_length);
        this.render();
        this.currentSortOrder = '';
        this.currentSearchParams = {
            search_file_name: '',
            search_created_by: '',
            file_format: ''
        };
        console.log("Files at initialization:", this.files.length);

        this.updateCheckboxes()
    }
    init() {
        this.restoreSelection();
        this.updateCheckboxes();
        this.updateSelectedCount();
    }

    saveSelectedFiles() {
        localStorage.setItem("selectedFiles", JSON.stringify(Array.from(this.selectedFiles)));
    }

    render() {
            const container = document.getElementById('file-container');
            if (!container) {
                console.error('File container not found');
                return;
            }

            container.innerHTML = `
                <div class="card-header">
                    <div class="card-content">
                        <div class="controls" style="margin-bottom:10px; font-weight:bold; font-size:12px; margin-left:12px;">
                            <span class="selected-count">${this.selectedFiles.size} files selected</span>
                        </div>
                    </div>
                    <div class="select-wrapper">
                        <span>Number of files to show:</span>
                        <select class="select file-count-select" id="fileLimitDropdown">
                            ${this.getSelectionOptions().map(opt => `
                                <option value="${opt}" ${opt === this.selectedCount ? 'selected' : ''}>
                                    ${opt === Math.max(...this.getSelectionOptions()) ? 'All' : opt}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                </div>
               
                <div class="w-100 table-wrapper">
                    <table class="table table-responsive w-100 intent-data intent-list-table">
                        <thead>
                            <tr>
                                <th>Id</th>
                                <th>File Name</th>
                                <th>Format</th>
                                <th>Size</th>
                                <th>Local path</th>
                                <th>Status</th>
                                <th>Created Date/By</th>
                                <th>Action</th>
                            </tr>
                            <tr>
                        <th style="font:bold;font-size:14px"> All <input type="checkbox" id="select-all" value="all"></th>
                        <th><input type="text" id="search_file_name" placeholder="Search File Name"></th>
                        <th><select id="file_format" class="form-control">
							<option value="">All</option>
							<option value="csv">csv</option>
							<option value="excel">excel</option>
							<option value="pdf">pdf</option>
							<option value="text">text</option>
							<option value="text">other</option>
						</select></th>
                        <th><div style="display: flex; align-items: center;">
								<div class="sort-icons" id="search_size" style="margin-left: 5px; display: flex;">
									<span id="sort-asc" class="material-symbols-outlined" style="cursor: pointer;color:#aaa;">arrow_upward</span>
      								<span id="sort-desc" class="material-symbols-outlined" style="cursor: pointer;color:#aaa;">arrow_downward</span>
								</div>
							</div>
						</th>
                        <th></th>
						<th></th>
                        <th><input type="text" id="search_created_by" placeholder="Search Created By"></th>
                        <th></th>
                    </tr>
                        </thead>
                        <tbody id="intent-table-body">
                            ${this.files.slice(0, this.selectedCount).map(file => this.createTableRow(file)).join('')}
                        </tbody>
                    </table>
                </div>
                  
        `;
        this.updatePagination(pagination,10)   
        this.attachEventListeners();
    }

    attachEventListeners() {
        document.querySelector('#intent-table-body')?.addEventListener('change', (e) => {
            if (e.target.classList.contains('select-item')) { 
                console.log("Checkbox clicked:", e.target.value, e.target.checked);
                this.toggleFileSelection(e.target.value, e.target.checked);
            }
        });
    
        document.querySelector('.file-count-select')?.addEventListener('change', (e) => {
            console.log("File count changed:", e.target.value);
            this.selectedCount = parseInt(e.target.value);
            this.updateFileList();
        });
    
        document.querySelector('#sort-asc')?.addEventListener('click', () => {
            console.log("Sort Asc Clicked");
            this.currentSortOrder = 'asc';
            this.fetchData();
            document.getElementById('sort-asc').style.color = '#24568f';
            document.getElementById('sort-desc').style.color = '#aaa';
        });
    
        document.querySelector('#sort-desc')?.addEventListener('click', () => {
            console.log("Sort Desc Clicked");
            this.currentSortOrder = 'desc';
            this.fetchData();
            document.getElementById('sort-desc').style.color = '#24568f';
            document.getElementById('sort-asc').style.color = '#aaa';
        });
    
        document.querySelector('#select-all')?.addEventListener('change', (e) => {
            console.log("Select All Checkbox Changed:", e.target.checked);
            this.handleBulkSelection(e.target.checked);
        });
    }
    

    fetchData(page = 1) {
        const selectedLimit = document.getElementById("fileLimitDropdown").value; // Get selected value

        console.log(displayLLMFilesUrl)
        $.ajax({
            url: this.displayLLMFilesUrl,
            type: 'GET',
            data: {
                page: page,
                limit:selectedLimit,
                search_file_name: this.currentSearchParams.search_file_name,
                search_created_by: this.currentSearchParams.search_created_by,
                file_format: this.currentSearchParams.file_format,
                sort_order: this.currentSortOrder
            },
            success: (data) => {                
                this.files = data.files;
                const rowsHtml = this.files.slice(0, this.selectedCount)
                .map(file => this.createTableRow(file)) // Assuming createTableRow is a method that creates HTML for each file
                .join('');
                console.log(this.selectedFiles.size)


            // Update the table body with the new rows
            $('#intent-table-body').html(rowsHtml);
            this.updateCheckboxes()
                        
             this.updatePagination(data.pagination,selectedLimit);
            },
            error: (xhr, status, error) => {
                console.error('AJAX request failed:', error);
            }
        });
    }

    updateFileList() {
        const selectedLimit = document.getElementById("fileLimitDropdown").value; // Get selected value
        $.ajax({
            url: this.displayLLMFilesUrl,
            type: "GET",
            data: {
                limit: selectedLimit,
                page: 1,
                search_file_name: this.currentSearchParams.search_file_name,
                search_created_by: this.currentSearchParams.search_created_by,
                file_format: this.currentSearchParams.file_format,
                sort_order: this.currentSortOrder
            },
            success: (data) => {
                localStorage.removeItem("selectedFiles");
                localStorage.removeItem("selectAllChecked");
                this.selectedFiles.clear();
                this.files = data.files;
                this.updateCheckboxes()
                const rowsHtml = this.files.slice(0, this.selectedCount)
                .map(file => this.createTableRow(file)) // Assuming createTableRow is a method that creates HTML for each file
                .join('');
                console.log(this.selectedFiles.size)
                $('.selected-count').text(this.selectedFiles.size + ` files selected`);


            // Update the table body with the new rows
            $('#intent-table-body').html(rowsHtml);                           
             this.updatePagination(data.pagination,selectedLimit);

                 // Re-attach the event listeners to the new table rows
            },
            error: () => {
                console.log("AJAX request failed");
            },
            
        });
    }
    handleBulkSelection(selectAll) {
        if (selectAll) {
            localStorage.setItem("selectAllChecked", "true");

            this.files.slice(0, this.selectedCount).forEach(file => {
                // Add file_id only if it doesn't already exist in selectedFiles
                this.selectedFiles.add(file.file_id);
                if (!this.selectedFiles.has(file.file_id)) {
                    alert(file.file_id)
                    this.selectedFiles.add(file.file_id);
                }
            });
        } else {
            localStorage.setItem("selectAllChecked", "false");
    
            this.files.slice(0, this.selectedCount).forEach(file => {
                // If file_id exists in selectedFiles, remove it; otherwise, add it
                
                    this.selectedFiles.delete(file.file_id); // Add if not present
               
            });
        }
    
        // Update UI
        this.updateCheckboxes();
        this.updateSelectedCount();
        this.saveSelectedFiles();
    }

        

    updateCheckboxes() {
        const allCheckboxes = document.querySelectorAll('.select-item');
        const selectedOnPage = new Set();
    
        // Update checkboxes based on selected files
        allCheckboxes.forEach(checkbox => {
            const fileId = checkbox.value;
            checkbox.checked = this.selectedFiles.has(fileId);
            
            // Track selected files on the current page
            if (checkbox.checked) {
                selectedOnPage.add(fileId);
            }
        });
        // Check if all visible files are selected, and set the select-all checkbox accordingly
        const selectAllCheckbox = document.querySelector('#select-all');
        const totalRecords = document.querySelectorAll("#intent-table-body tr").length;

        const isSelectAllChecked = selectedOnPage.size == totalRecords 

        console.log(this.isSelectAllChecked,selectedOnPage.size,this.selectedCount,totalRecords)
        selectAllCheckbox.checked = isSelectAllChecked;
        console.log("Select All Checked:", selectAllCheckbox.checked);
    }

    updateSelectedCount() {
        document.querySelector('.selected-count').textContent = `${this.selectedFiles.size} files selected`;
    }

    toggleFileSelection(fileId, isSelected) {
        if (isSelected) {
            console.log(fileId)
            this.selectedFiles.add(fileId);

        } else {
            this.selectedFiles.delete(fileId);
        }

        this.updateCheckboxes();
        this.updateSelectedCount();
        this.saveSelectedFiles();
    }
    restoreSelection() {
        const isSelectAllChecked = localStorage.getItem("selectAllChecked") === "true";

        if (isSelectAllChecked) {
            this.handleBulkSelection(true);
        } else {
            this.selectedFiles.forEach(fileId => {
                const checkbox = document.querySelector(`.select-item[value="${fileId}"]`);
                console.log(checkbox.checked)
                if (checkbox) checkbox.checked = true;
            });
        }
    }
    getSelectionOptions() {
        const maxFiles = file_length;

        const options = [];
        for (let i = 10; i <= maxFiles; i += 10) {
            options.push(i);
        }
        if (!options.includes(maxFiles) && maxFiles % 10 !== 0) {
            options.push(maxFiles);
        }
        return options;
    }

    createTableRow(file) {
        let statusClass = file.status.toLowerCase() === "pending" ? "status-badge-untrain" : "status-badge";

        let deleteAction = file.status.toLowerCase() === "embedded" 
        ? `<div class="d-flex align-items-baseline action-popup__delete" onclick="delete_embedded_file('${file.file_id}')">
                <img src="static/assets/img/icons/delete_icon.svg" alt="delete" style="width:17px;margin-left:5px">
           </div>`
        : `<div class="d-flex align-items-baseline action-popup__delete" onclick="delete_file('${file.file_id}')">
                <img src="static/assets/img/icons/delete_icon.svg" alt="delete" style="width:17px;margin-left:5px">
           </div>`;

        return `
            <tr>
                <td style="font:bold;font-size:14px;display:flex;gap:5px;">
                    ${file.id} 
                    <input type="checkbox" class="select-item" value="${file.file_id}" ${this.selectedFiles.has(file.file_id) ? 'checked' : ''}>
                </td>
                <td>${file.name}</td>
                <td>${file.format}</td>
                <td>${file.size}</td>
                <td>${file.path}</td>
                <td><div class="${statusClass}">${file.status}</div></td>
                <td>${file.upload_date} <br> ${file.created_by}</td>
                <td>
                    <div>
                        <div class="d-flex align-items-baseline action-popup__edit" style="float:left;">
                            <a href="/view_file/${file.file_id}" target="_blank">
                                <img src="static/assets/img/icons/view-com.svg" alt="View" style="width:20px;">
                            </a>
                        </div>
                        ${deleteAction}
                    </div>
                </td>
            </tr>
        `;
    }


    updatePagination(pagination,limit) {
        let paginationHtml = '<div class="pagination-wrapper__left"></div><nav><ul class="pagination">';
    
        if (pagination.has_prev) {
            paginationHtml += `<li class="page-item"><a class="page-link" href="/display_llm_files?page=${pagination.prev_page}"  data-page="${pagination.prev_page}">«</a></li>`;
        } else {
            paginationHtml += `<li class="page-item disabled"><span class="page-link">«</span></li>`;
        }
    
        pagination.page_numbers.forEach(page => {
            if (page === pagination.current_page) {
                paginationHtml += `<li class="page-item active"><span class="page-link">${page}</span></li>`;
            } else {
                paginationHtml += `<li class="page-item"><a class="page-link" href="/display_llm_files?page=${page}&limit=${limit}" data-page="${page}">${page}</a></li>`;
            }
        });
    
        if (pagination.has_next) {
            paginationHtml += `<li class="page-item"><a class="page-link" href="/display_llm_files?page=${pagination.next_page}" data-page="${pagination.next_page}">»</a></li>`;
        } else {
            paginationHtml += `<li class="page-item disabled"><span class="page-link">»</span></li>`;
        }
    
        paginationHtml += '</ul></nav>';
        $(".pagination-wrapper").html(paginationHtml);
        this.attachPaginationListeners();

    }

    attachPaginationListeners() {
        document.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                this.fetchData(page);
            });
        });
    }
    
}