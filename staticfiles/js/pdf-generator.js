/**
 * pdf-generator.js - Version améliorée pour une meilleure mise en page
 */

// S'assurer que le DOM est entièrement chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser le bouton de génération PDF
    const generateButton = document.getElementById('generate-pdf-button');
    if (generateButton) {
        generateButton.addEventListener('click', generateContractPDF);
    }
});

/**
 * Génère le PDF du contrat avec une mise en page optimisée
 */
async function generateContractPDF() {
    try {
        // Afficher l'indicateur de chargement
        showLoading();
        
        // 1. Attendre que toutes les ressources soient chargées
        await document.fonts.ready;
        await waitForImages();
        
        // 2. Appliquer temporairement les styles d'impression et préparation de page
        const printStylesheet = applyPrintStyles();
        
        // 3. Capturer le contenu HTML avec html2canvas
        const element = document.getElementById('contract-document');
        const canvas = await html2canvas(element, {
            scale: 2, // Résolution doublée pour meilleure qualité
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#FFFFFF',
            // Minimiser la mise en cache pour plus de précision
            logging: false,
            removeContainer: false,
            // Améliorer la qualité du rendu
            imageTimeout: 0,
            onclone: prepareClone
        });
        
        // 4. Restaurer les styles originaux
        if (printStylesheet) {
            printStylesheet.remove();
        }
        
        // 5. Créer le PDF avec jsPDF
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4',
            compress: true,
            precision: 16
        });
        
        // 6. Ajouter l'image du canvas au PDF avec pagination optimisée
        const imgData = canvas.toDataURL('image/jpeg', 1.0); // Meilleure qualité
        const imgWidth = 210; // Largeur A4 en mm
        const pageHeight = 297; // Hauteur A4 en mm
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        // Pagination optimisée
        let heightLeft = imgHeight;
        let position = 0;
        let page = 1;
        
        // Ajouter la première page
        pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
        
        // Ajouter les pages suivantes si nécessaire
        while (heightLeft > 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;
            page++;
        }
        
        // 7. Télécharger le PDF
        const agreementNumber = document.getElementById('agreement-number')?.textContent || 'contract';
        pdf.save(`${agreementNumber}.pdf`);
        
        // 8. Masquer l'indicateur de chargement
        hideLoading();
        
    } catch (error) {
        console.error('Erreur lors de la génération du PDF:', error);
        hideLoading();
        alert('Une erreur est survenue lors de la génération du PDF.');
    }
}

/**
 * Prépare le clone du document pour une meilleure impression
 * @param {Document} doc - Document cloné
 */
function prepareClone(doc) {
    // Ajouter les sauts de page aux bons endroits
    const sections = doc.querySelectorAll('.section');
    
    // Prédéfinir des zones de saut de page après certaines sections
    const breakAfterSections = [3, 6, 9]; // Après les sections 3, 6 et 9
    
    breakAfterSections.forEach(sectionIndex => {
        if (sections[sectionIndex]) {
            const pageBreak = doc.createElement('div');
            pageBreak.className = 'page-break';
            sections[sectionIndex].after(pageBreak);
        }
    });
    
    // S'assurer que les signatures sont bien positionnées
    const signatureArea = doc.querySelector('.signature-area');
    if (signatureArea) {
        // Vérifier si la zone de signature est proche d'un saut de page potentiel
        const signatureTop = signatureArea.getBoundingClientRect().top;
        const pageHeight = 297 * 3.78; // Conversion approximative mm -> px
        
        // Si la signature est trop proche de la fin de page, forcer un saut avant
        if ((signatureTop % pageHeight) > pageHeight - 150) {
            const pageBreak = doc.createElement('div');
            pageBreak.className = 'page-break';
            signatureArea.before(pageBreak);
        }
    }
    
    return doc;
}

/**
 * Applique les styles d'impression et retourne la feuille de style
 * @returns {HTMLElement} Élément de style ajouté
 */
function applyPrintStyles() {
    const printStyle = document.createElement('style');
    printStyle.id = 'temp-print-style';
    
    // Styles additionnels pour l'impression
    printStyle.textContent = `
        body {
            background-color: white !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .contract-container {
            box-shadow: none !important;
            width: 210mm !important;
        }
        
        .no-print {
            display: none !important;
        }
        
        /* Forcer les pages à se terminer au bon endroit */
        .page-break {
            page-break-after: always;
            break-after: page;
            height: 0;
            display: block;
        }
        
        /* Éviter les sauts de page inappropriés */
        .signature-area, .payment-info, h1, h2, h3, 
        .info-box, .section-title, .witness-section {
            break-inside: avoid;
            page-break-inside: avoid;
        }
        
        /* S'assurer que les titres restent avec leur contenu */
        h1, h2, h3 {
            break-after: avoid;
            page-break-after: avoid;
        }
    `;
    
    document.head.appendChild(printStyle);
    return printStyle;
}

/**
 * Attend que toutes les images soient chargées
 * @returns {Promise<void>}
 */
function waitForImages() {
    return new Promise((resolve) => {
        const images = document.querySelectorAll('#contract-document img');
        
        if (images.length === 0) {
            resolve();
            return;
        }
        
        let loadedImages = 0;
        const totalImages = images.length;
        
        const imageLoaded = () => {
            loadedImages++;
            if (loadedImages === totalImages) {
                resolve();
            }
        };
        
        images.forEach(img => {
            if (img.complete) {
                imageLoaded();
            } else {
                img.addEventListener('load', imageLoaded);
                img.addEventListener('error', imageLoaded);
            }
        });
    });
}

/**
 * Affiche un indicateur de chargement
 */
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'pdf-loading';
    loadingDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    loadingDiv.innerHTML = `
        <div style="background-color: white; padding: 20px; border-radius: 5px; text-align: center;">
            <p>Génération du PDF en cours...</p>
            <div style="margin: 10px auto; width: 40px; height: 40px; border: 4px solid #f3f3f3; 
                 border-top: 4px solid #0B3C5D; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        </div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
    
    document.body.appendChild(loadingDiv);
}

/**
 * Masque l'indicateur de chargement
 */
function hideLoading() {
    const loadingDiv = document.getElementById('pdf-loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}