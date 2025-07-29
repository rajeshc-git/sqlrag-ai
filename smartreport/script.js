document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const patientForm = document.getElementById('patientForm');
    const patientNumber = document.getElementById('patientNumber');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const patientReport = document.getElementById('patientReport');
    const printReportBtn = document.getElementById('printReport');
    
    // Patient Data Elements
    const patientNameEl = document.getElementById('patientName');
    const patientIdEl = document.getElementById('patientId');
    const patientAgeEl = document.getElementById('patientAge');
    const patientGenderEl = document.getElementById('patientGender');
    const patientStatusEl = document.getElementById('patientStatus');
    
    // Tab Content Elements
    const summaryContent = document.getElementById('summaryContent');
    const demographicsContent = document.getElementById('demographicsContent');
    const visitsTableBody = document.getElementById('visitsTableBody');
    const recommendationsContent = document.getElementById('recommendationsContent');
    const rawDataContent = document.getElementById('rawDataContent');
    
    // Event Listeners
    patientForm.addEventListener('submit', fetchPatientData);
    printReportBtn.addEventListener('click', printReport);
    
    // If patient number is in URL parameter, auto-fill and fetch
    const urlParams = new URLSearchParams(window.location.search);
    const patientParam = urlParams.get('patientNumber');
    if (patientParam) {
        patientNumber.value = patientParam;
        fetchPatientData(new Event('submit'));
    }
    
    /**
     * Fetches patient data from the backend API
     * @param {Event} event - Form submission event
     */
    function fetchPatientData(event) {
        event.preventDefault();
        
        const patientNum = patientNumber.value.trim();
        if (!patientNum) {
            showError('Please enter a patient number');
            return;
        }
        
        // Show loading spinner, hide other sections
        loadingSpinner.classList.remove('d-none');
        errorAlert.classList.add('d-none');
        patientReport.classList.add('d-none');
        
        // Fetch data from our backend proxy API
        fetch(`https://blueshift.abi-health.com:3000/patientnumber/${patientNum}`, {
    method: 'GET',
    headers: {
        'x-api-key': 'q1riHeoxylJy41TqzOXT75rty/yGU2e1pk+0GGFMrTUJ3fB67uIQXGzC47dvg6s3iSnczDxsK9fm+AStHt9ZDQ==',
        'Content-Type': 'application/json'
    }
})
.then(response => {
    if (!response.ok) {
        return response.json().then(data => {
            throw new Error(data.error || `Failed to retrieve data (${response.status})`);
        });
    }
    return response.json();
})
.then(data => {
    processPatientData(data);
    loadingSpinner.classList.add('d-none');
    patientReport.classList.remove('d-none');
})
.catch(error => {
    loadingSpinner.classList.add('d-none');
    showError(error.message);
});

    }
    
    /**
     * Processes and displays patient data in the report
     * @param {Object} data - Patient data from API
     */
    function processPatientData(data) {
        // Store raw data
        rawDataContent.textContent = JSON.stringify(data, null, 2);
        
        // Get demographics and visit information
        const demographics = data.PatientDemographics && data.PatientDemographics.length > 0 
            ? data.PatientDemographics[0] 
            : null;
            
        const visits = data.PatientVisits || [];
        
        // Handle case where no demographics are found
        if (!demographics) {
            showError('No patient demographic information found');
            return;
        }
        
        // Set header information
        patientNameEl.textContent = demographics.PNAME || 'Unknown';
        patientIdEl.textContent = `Patient ID: ${demographics.PATIENTID || 'Unknown'}`;
        
        // Calculate age if DOB exists
        let ageText = 'Age: Unknown';
        if (demographics.DOB) {
            const dob = new Date(demographics.DOB);
            const ageDiff = Date.now() - dob.getTime();
            const ageDate = new Date(ageDiff);
            const age = Math.abs(ageDate.getUTCFullYear() - 1970);
            ageText = `Age: ${age} years`;
        }
        patientAgeEl.textContent = ageText;
        
        // Set gender
        const genderMap = {
            'M': 'Male',
            'F': 'Female',
            'O': 'Other'
        };
        patientGenderEl.textContent = `Gender: ${genderMap[demographics.SEX] || demographics.SEX || 'Unknown'}`;
        
        // Set status
        const statusMap = {
            'A': 'Active',
            'I': 'Inactive'
        };
        patientStatusEl.textContent = `Status: ${statusMap[demographics.PatientStatus] || demographics.PatientStatus || 'Unknown'}`;
        
        // Generate summary content
        generateSummary(demographics, visits, data);
        
        // Generate demographics content
        generateDemographics(demographics);
        
        // Generate visits table
        generateVisitsTable(visits);
        
        // Generate recommendations
        generateRecommendations(data);
    }
    
    /**
     * Generates a summary of the patient information
     * @param {Object} demographics - Patient demographics
     * @param {Array} visits - Patient visits
     * @param {Object} fullData - Complete patient data
     */
    function generateSummary(demographics, visits, fullData) {
        // Calculate age
        let age = "Unknown";
        if (demographics.DOB) {
            const dob = new Date(demographics.DOB);
            const ageDiff = Date.now() - dob.getTime();
            const ageDate = new Date(ageDiff);
            age = Math.abs(ageDate.getUTCFullYear() - 1970);
        }
        
        // Format registration date
        let registrationDate = "Unknown";
        if (demographics.RegistrationDTTM) {
            registrationDate = new Date(demographics.RegistrationDTTM).toLocaleDateString('en-US', {
                year: 'numeric', 
                month: 'long', 
                day: 'numeric'
            });
        }
        
        // Count visits
        const visitCount = visits.length;
        
        // Get most recent visit
        let lastVisitDate = "No visits recorded";
        if (visitCount > 0) {
            // Find the most recent visit by comparing dates
            const mostRecentVisit = visits.reduce((latest, current) => {
                const latestDate = new Date(latest.VisitDate || latest.PVDate);
                const currentDate = new Date(current.VisitDate || current.PVDate);
                return currentDate > latestDate ? current : latest;
            });
            
            lastVisitDate = new Date(mostRecentVisit.VisitDate || mostRecentVisit.PVDate).toLocaleDateString('en-US', {
                year: 'numeric', 
                month: 'long', 
                day: 'numeric'
            });
        }
        
        // Create the summary HTML
        let summaryHTML = `
            <div class="row g-4">
                <div class="col-md-6">
                    <div class="d-flex align-items-center mb-3">
                        <i class="fas fa-user-circle fs-1 text-primary me-3"></i>
                        <div>
                            <h4 class="mb-0">${demographics.PNAME || 'Unknown'}</h4>
                            <p class="text-muted mb-0">${age} years old, ${demographics.SEX === 'M' ? 'Male' : demographics.SEX === 'F' ? 'Female' : demographics.SEX || 'Unknown'}</p>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <p class="mb-1"><span class="info-label">Patient ID:</span> ${demographics.PATIENTID || 'Unknown'}</p>
                        <p class="mb-1"><span class="info-label">Patient Number:</span> ${visits.length > 0 ? visits[0].PatientNumber : 'Unknown'}</p>
                        <p class="mb-1"><span class="info-label">Registration Date:</span> ${registrationDate}</p>
                        <p class="mb-1"><span class="info-label">Status:</span> ${demographics.PatientStatus === 'A' ? 'Active' : demographics.PatientStatus === 'I' ? 'Inactive' : demographics.PatientStatus || 'Unknown'}</p>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <h5><i class="fas fa-calendar-check text-primary me-2"></i>Visit Summary</h5>
                    <div class="card bg-light">
                        <div class="card-body">
                            <div class="row text-center g-3">
                                <div class="col-6">
                                    <h2 class="mb-0 fw-bold">${visitCount}</h2>
                                    <p class="mb-0 text-muted">Total Visits</p>
                                </div>
                                <div class="col-6">
                                    <h5 class="mb-0">${lastVisitDate}</h5>
                                    <p class="mb-0 text-muted">Last Visit</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <hr class="my-4">
            
            <div class="alert alert-info" role="alert">
                <i class="fas fa-info-circle me-2"></i>
                <strong>This is a medical summary report</strong> generated based on the available patient data. 
                Please consult with a healthcare professional for interpretation of medical information.
            </div>
        `;
        
        summaryContent.innerHTML = summaryHTML;
    }
    
    /**
     * Generates demographic information display
     * @param {Object} demographics - Patient demographics
     */
    function generateDemographics(demographics) {
        // Format date of birth
        let formattedDOB = "Unknown";
        if (demographics.DOB) {
            formattedDOB = new Date(demographics.DOB).toLocaleDateString('en-US', {
                year: 'numeric', 
                month: 'long', 
                day: 'numeric'
            });
        }
        
        // Format registration date
        let registrationDate = "Unknown";
        if (demographics.RegistrationDTTM) {
            registrationDate = new Date(demographics.RegistrationDTTM).toLocaleDateString('en-US', {
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        
        // Define demographic field mapping for display
        const demographicFields = [
            { label: "Patient ID", value: demographics.PATIENTID },
            { label: "Full Name", value: demographics.PNAME },
            { label: "Date of Birth", value: formattedDOB },
            { label: "Gender", value: demographics.SEX === 'M' ? 'Male' : demographics.SEX === 'F' ? 'Female' : demographics.SEX },
            { label: "Email", value: demographics.EMail || 'Not provided' },
            { label: "Title", value: demographics.TITLECode },
            { label: "Registration Date", value: registrationDate },
            { label: "Patient Status", value: demographics.PatientStatus === 'A' ? 'Active' : demographics.PatientStatus === 'I' ? 'Inactive' : demographics.PatientStatus }
        ];
        
        // Create HTML for demographics
        let demographicsHTML = '';
        
        demographicFields.forEach(field => {
            demographicsHTML += `
                <div class="col-md-6 mb-3">
                    <p class="mb-1 fw-bold">${field.label}:</p>
                    <p class="border-bottom pb-2">${field.value || 'Not available'}</p>
                </div>
            `;
        });
        
        // Add any additional demographic information that might be available
        const additionalFields = Object.keys(demographics).filter(key => 
            !['PATIENTID', 'PNAME', 'DOB', 'SEX', 'EMail', 'TITLECode', 
              'RegistrationDTTM', 'PatientStatus', 'CreatedAt'].includes(key)
        );
        
        if (additionalFields.length > 0) {
            demographicsHTML += `
                <div class="col-12 mt-3">
                    <h5>Additional Information</h5>
                    <div class="row">
            `;
            
            additionalFields.forEach(key => {
                // Format the key for display (CamelCase to Title Case)
                const formattedKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
                
                // Format values if they look like dates
                let value = demographics[key];
                if (typeof value === 'string' && (value.includes('T') && value.includes('Z') || value.includes('-'))) {
                    try {
                        const date = new Date(value);
                        if (!isNaN(date.getTime())) {
                            value = date.toLocaleDateString('en-US', {
                                year: 'numeric', 
                                month: 'long', 
                                day: 'numeric'
                            });
                        }
                    } catch (e) {
                        // Keep original value if date parsing fails
                    }
                }
                
                demographicsHTML += `
                    <div class="col-md-6 mb-3">
                        <p class="mb-1 fw-bold">${formattedKey}:</p>
                        <p class="border-bottom pb-2">${value || 'Not available'}</p>
                    </div>
                `;
            });
            
            demographicsHTML += `
                    </div>
                </div>
            `;
        }
        
        demographicsContent.innerHTML = demographicsHTML;
    }
    
    /**
     * Generates visit history table
     * @param {Array} visits - Patient visits
     */
    function generateVisitsTable(visits) {
        if (!visits || visits.length === 0) {
            visitsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4">
                        <i class="fas fa-calendar-times text-muted me-2"></i>
                        No visit records found for this patient
                    </td>
                </tr>
            `;
            return;
        }
        
        // Sort visits by date (most recent first)
        visits.sort((a, b) => {
            const dateA = new Date(a.VisitDate || a.PVDate);
            const dateB = new Date(b.VisitDate || b.PVDate);
            return dateB - dateA;
        });
        
        let tableHTML = '';
        
        visits.forEach(visit => {
            // Format date
            const visitDate = new Date(visit.VisitDate || visit.PVDate).toLocaleDateString('en-US', {
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            tableHTML += `
                <tr>
                    <td>${visit.PatientVisitID || 'N/A'}</td>
                    <td>${visit.VisitNumber || 'N/A'}</td>
                    <td>${visitDate}</td>
                    <td>Org ID: ${visit.OrgId || 'N/A'}</td>
                    <td>${visit.ReferingPhysicianName || 'Not specified'}</td>
                </tr>
            `;
        });
        
        visitsTableBody.innerHTML = tableHTML;
    }
    
    /**
     * Generates recommendations based on patient data
     * @param {Object} data - Complete patient data
     */
    function generateRecommendations(data) {
        // Check if there are any specific recommendations in the data
        // This is hypothetical since we don't know the exact structure of recommendations
        const hasRecommendations = false; // Replace with actual check if data contains recommendations
        
        if (hasRecommendations) {
            // Display actual recommendations from data
            // This would need to be customized based on the actual data structure
            recommendationsContent.innerHTML = `
                <p>Specific recommendations would be displayed here.</p>
            `;
        } else {
            // Generate general recommendations based on available data
            const demographics = data.PatientDemographics && data.PatientDemographics.length > 0 
                ? data.PatientDemographics[0] 
                : null;
                
            // Get patient age
            let age = null;
            if (demographics && demographics.DOB) {
                const dob = new Date(demographics.DOB);
                const ageDiff = Date.now() - dob.getTime();
                const ageDate = new Date(ageDiff);
                age = Math.abs(ageDate.getUTCFullYear() - 1970);
            }
            
            // Get gender
            const gender = demographics ? demographics.SEX : null;
            
            // Generate some generic recommendations based on age and gender
            let recommendationsHTML = `
                <div class="alert alert-warning mb-4">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Note:</strong> No specific medical recommendations were found in the patient data. 
                    The following are general health recommendations and should not replace professional medical advice.
                </div>
                
                <div class="row g-4">
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h5 class="mb-0"><i class="fas fa-heartbeat text-danger me-2"></i>General Health</h5>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">Maintain regular check-ups with your healthcare provider</li>
                                    <li class="list-group-item">Stay active with at least 150 minutes of moderate exercise per week</li>
                                    <li class="list-group-item">Eat a balanced diet rich in fruits, vegetables, and whole grains</li>
                                    <li class="list-group-item">Get 7-9 hours of sleep per night</li>
                                    <li class="list-group-item">Manage stress through relaxation techniques or mindfulness</li>
                                </ul>
                            </div>
                        </div>
                    </div>
            `;
            
            // Age-specific recommendations
            if (age !== null) {
                let ageRecommendations = [];
                
                if (age < 18) {
                    ageRecommendations = [
                        "Regular growth and development check-ups",
                        "Ensure all vaccinations are up to date",
                        "Promote physical activity and healthy eating habits",
                        "Monitor screen time and promote good sleep habits",
                        "Regular dental check-ups every 6 months"
                    ];
                } else if (age >= 18 && age < 40) {
                    ageRecommendations = [
                        "Blood pressure screening at least every 2 years",
                        "Cholesterol test every 4-6 years",
                        "Annual flu vaccination",
                        "Skin examination for unusual moles or skin changes",
                        "Mental health screening"
                    ];
                } else if (age >= 40 && age < 65) {
                    ageRecommendations = [
                        "Blood pressure screening annually",
                        "Cholesterol test every 1-2 years",
                        "Blood glucose test every 3 years",
                        "Colorectal cancer screening starting at age 45",
                        "Annual flu vaccination and pneumonia vaccination as recommended"
                    ];
                } else {
                    ageRecommendations = [
                        "Annual wellness visit",
                        "Blood pressure screening annually",
                        "Cholesterol test annually",
                        "Blood glucose test annually",
                        "Bone density test as recommended",
                        "Annual flu vaccination and other age-appropriate vaccinations"
                    ];
                }
                
                recommendationsHTML += `
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h5 class="mb-0"><i class="fas fa-user-clock text-primary me-2"></i>Age-Specific (${age} years)</h5>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                `;
                
                ageRecommendations.forEach(rec => {
                    recommendationsHTML += `<li class="list-group-item">${rec}</li>`;
                });
                
                recommendationsHTML += `
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Gender-specific recommendations
            if (gender === 'F' || gender === 'M') {
                let genderRecommendations = [];
                
                if (gender === 'F') {
                    if (age && age >= 21) {
                        genderRecommendations = [
                            "Cervical cancer screening (Pap test) every 3 years",
                            "Clinical breast exam annually",
                            "Mammogram screening as recommended by your provider",
                            "Osteoporosis screening as recommended",
                            "Consider HPV vaccination if not previously received"
                        ];
                    } else {
                        genderRecommendations = [
                            "Consider HPV vaccination as recommended",
                            "Discuss reproductive health with your healthcare provider",
                            "Consider birth control options if applicable"
                        ];
                    }
                } else if (gender === 'M') {
                    if (age && age >= 50) {
                        genderRecommendations = [
                            "Prostate cancer screening discussion with your doctor",
                            "Abdominal aortic aneurysm screening once between ages 65-75 if you've ever smoked",
                            "Monitor for urinary and sexual health concerns"
                        ];
                    } else {
                        genderRecommendations = [
                            "Testicular self-examination monthly",
                            "Discussion about reproductive health with your provider",
                            "Monitor for urinary and sexual health concerns"
                        ];
                    }
                }
                
                recommendationsHTML += `
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h5 class="mb-0">
                                    <i class="fas ${gender === 'F' ? 'fa-venus' : 'fa-mars'} text-${gender === 'F' ? 'danger' : 'primary'} me-2"></i>
                                    ${gender === 'F' ? 'Women\'s' : 'Men\'s'} Health
                                </h5>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                `;
                
                genderRecommendations.forEach(rec => {
                    recommendationsHTML += `<li class="list-group-item">${rec}</li>`;
                });
                
                recommendationsHTML += `
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            recommendationsHTML += `
                </div>
                
                <div class="mt-4 alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    These recommendations are general guidelines. Please consult with your healthcare provider for 
                    personalized recommendations based on your specific health needs and medical history.
                </div>
            `;
            
            recommendationsContent.innerHTML = recommendationsHTML;
        }
    }
    
    /**
     * Displays an error message
     * @param {string} message - Error message to display
     */
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
        patientReport.classList.add('d-none');
    }
    
    /**
     * Prints the patient report
     */
    function printReport() {
        window.print();
    }
});
