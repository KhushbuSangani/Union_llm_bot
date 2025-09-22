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
            search_query: '',
            search_response: ''


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
                            <span class="selected-count hidden">${this.selectedFiles.size} files selected</span>
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
                                <th>Query</th>
                                <th>Response</th>
                                <th>File Name</th>
                                <th>Sent By</th>
                                <th>Send Date</th>
                            </tr>
                            <tr>
                        <th style="font:bold;font-size:14px">  <input type="checkbox" id="select-all" value="all" class="hidden"></th>
                        <th><input type="text" id="search_query" placeholder="Search Query"></th>
                        <th><input type="text" id="search_response" placeholder="Search Response"></th>
                        <th><input type="text" id="search_file_name" placeholder="Search FileName"></th>
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
                search_query: this.currentSearchParams.search_query,
                search_response: this.currentSearchParams.search_response
            },
            success: (data) => {    
                this.files = data.data
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
                search_query: this.currentSearchParams.search_query,
                search_response: this.currentSortOrder.search_response
            },
            success: (data) => {
                localStorage.removeItem("selectedFiles");
                localStorage.removeItem("selectAllChecked");
                this.selectedFiles.clear();
                this.files = data.data;
            
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
                // Add cache_id only if it doesn't already exist in selectedFiles
                this.selectedFiles.add(file.cache_id);
                if (!this.selectedFiles.has(file.cache_id)) {
                    alert(file.cache_id)
                    this.selectedFiles.add(file.cache_id);
                }
            });
        } else {
            localStorage.setItem("selectAllChecked", "false");
    
            this.files.slice(0, this.selectedCount).forEach(file => {
                // If cache_id exists in selectedFiles, remove it; otherwise, add it
                
                    this.selectedFiles.delete(file.cache_id); // Add if not present
               
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
        const checkboxChecked = this.selectedFiles.has(file.cache_id) ? 'checked' : '';
        return `
            <tr>
                <td style="font-weight:bold; font-size:14px;">
                    ${file.id}
                    <input type="checkbox" class="select-item hidden" value="${file.cache_id}" ${checkboxChecked}>
                </td>
                <td>${file.query}</td>
                <td>${file.response}</td>
                <td>${file.file_name}</td>
                <td>${file.created_by}</td>
                <td>${file.send_date}</td>
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