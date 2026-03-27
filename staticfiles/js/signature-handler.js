/**
 * signature-handler.js - Affichage des signatures dans le contrat
 * Gère les 3 types de signatures : typographie, dessin et image uploadée
 */

// Initialiser les signatures quand le document est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Afficher la signature de l'interprète
    renderInterpreterSignature();
    
    // Afficher la signature de l'entreprise
    renderCompanySignature();
});

/**
 * Affiche la signature de l'interprète selon son type
 */
function renderInterpreterSignature() {
    // Conteneur de signature
    const signatureContainer = document.getElementById('interpreter-signature');
    if (!signatureContainer) return;
    
    // Récupérer le type de signature
    const signatureData = document.querySelector('.signature-data');
    if (!signatureData) return;
    
    const signatureType = signatureData.dataset.signatureType;
    
    // Afficher selon le type
    switch (signatureType) {
        case 'type':
            // Signature typographique
            const text = signatureData.dataset.signatureText;
            const font = signatureData.dataset.signatureFont || 'font-script';
            
            signatureContainer.innerHTML = `
                <div class="typography-signature ${font}">${text}</div>
            `;
            break;
            
        case 'draw':
            // Signature dessinée
            const drawnData = signatureData.dataset.signatureDrawnData;
            if (drawnData) {
                try {
                    const points = JSON.parse(drawnData);
                    const svg = convertPointsToSVG(points);
                    signatureContainer.innerHTML = `
                        <div class="drawn-signature">${svg}</div>
                    `;
                } catch (error) {
                    console.error('Erreur de parsing des données de signature dessinée', error);
                    signatureContainer.innerHTML = '<div class="signature-error">Signature non disponible</div>';
                }
            }
            break;
            
        case 'upload':
            // Image de signature uploadée
            const imageUrl = signatureData.dataset.signatureImageUrl;
            if (imageUrl) {
                signatureContainer.innerHTML = `
                    <div class="uploaded-signature">
                        <img src="${imageUrl}" alt="Signature" />
                    </div>
                `;
            }
            break;
            
        default:
            signatureContainer.innerHTML = '<div class="signature-placeholder">Signature</div>';
    }
}

/**
 * Affiche la signature du représentant de l'entreprise
 */
function renderCompanySignature() {
    const companySignatureContainer = document.getElementById('company-signature');
    if (!companySignatureContainer) return;
    
    // Récupérer le nom du représentant depuis l'attribut data
    const representativeName = companySignatureContainer.dataset.companyRepresentative || 'Marc-Henry Valme';
    
    // Afficher en utilisant Helvetica
    companySignatureContainer.innerHTML = representativeName;
    
    // S'assurer que la police Helvetica est appliquée
    companySignatureContainer.style.fontFamily = 'Helvetica, Arial, sans-serif';
}

/**
 * Convertit les points de dessin en image SVG
 * @param {Array} points - Tableau de points du dessin
 * @returns {string} Code SVG de la signature
 */
function convertPointsToSVG(points) {
    if (!points || !points.length) {
        return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50"></svg>';
    }
    
    // Trouver les dimensions
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;
    
    // Parcourir tous les points pour trouver les limites
    points.forEach(segment => {
        segment.forEach(point => {
            minX = Math.min(minX, point.x);
            minY = Math.min(minY, point.y);
            maxX = Math.max(maxX, point.x);
            maxY = Math.max(maxY, point.y);
        });
    });
    
    // Ajouter une marge
    const margin = 5;
    minX -= margin;
    minY -= margin;
    maxX += margin;
    maxY += margin;
    
    // Dimensions du SVG
    const width = maxX - minX;
    const height = maxY - minY;
    
    // Créer le chemin SVG
    let pathData = '';
    points.forEach(segment => {
        if (segment.length > 0) {
            // Déplacer au premier point
            pathData += `M${segment[0].x - minX},${segment[0].y - minY} `;
            
            // Tracer des lignes vers les points suivants
            for (let i = 1; i < segment.length; i++) {
                pathData += `L${segment[i].x - minX},${segment[i].y - minY} `;
            }
        }
    });
    
    // Renvoyer le SVG complet
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <path d="${pathData}" stroke="#000000" stroke-width="2" fill="none" />
    </svg>`;
}