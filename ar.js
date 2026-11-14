/* ar.js — shared Arabic i18n for all detail pages */
(function () {
  var UI = {
    fr: {
      'nav-back':        'Retour au stock',
      'bc-home':         'Accueil',
      'bc-stock':        'Stock',
      'price-label':     'Prix',
      'price-contact':   'Contactez-nous pour le prix',
      'price-request':   'Sur demande',
      'price-sur-cmd':   'Sur commande',
      'price-showroom':  'Prix au showroom',
      'ccurr-enquire':   'Renseignez-vous en agence',
      'spec-title':      'Fiche technique',
      'spec-marque':     'Marque',
      'spec-modele':     'Modèle',
      'spec-annee':      'Année',
      'spec-carrosserie':'Carrosserie',
      'spec-km':         'Kilométrage',
      'spec-etat':       'État',
      'spec-couleur':    'Couleur',
      'spec-places':     'Places',
      'spec-carburant':  'Carburant',
      'spec-cylindree':  'Cylindrée',
      'spec-transmission':'Transmission',
      'spec-dispo':      'Disponibilité',
      'sec-motorisation':'Motorisation',
      'spec-moteur':     'Moteur',
      'spec-puissance':  'Puissance',
      'spec-couple':     'Couple',
      'spec-boite':      'Boîte',
      'spec-traction':   'Traction',
      'spec-0100':       '0–100 km/h',
      'spec-vmax':       'Vitesse max',
      'spec-conso':      'Consommation',
      'sec-equip':       'Équipements & technologie',
      'sec-confort':     'Confort & options',
      'sec-securite':    'Sécurité',
      'gallery-label':   'Galerie photos',
      'gallery-title':   'Toutes les photos',
      'cta-wa':          'Nous contacter sur WhatsApp',
      'cta-back':        "Voir d'autres véhicules",
      'footer-tag':      'Showroom Premium — Batna - Centre-ville',
      'footer-copy':     '© 2026 Kinan Cars. Tous droits réservés.',
      'occasion-txt':    'Occasion',
      'neuf-txt':        'Neuf',
      'dispo-txt':       'Immédiate',
    },
    ar: {
      'nav-back':        'العودة إلى المخزون',
      'bc-home':         'الرئيسية',
      'bc-stock':        'المخزون',
      'price-label':     'السعر',
      'price-contact':   'تواصلوا معنا للحصول على السعر',
      'price-request':   'عند الطلب',
      'price-sur-cmd':   'بالطلب',
      'price-showroom':  'السعر في المعرض',
      'ccurr-enquire':   'استفسر في الوكالة',
      'spec-title':      'المواصفات التقنية',
      'spec-marque':     'العلامة',
      'spec-modele':     'النموذج',
      'spec-annee':      'السنة',
      'spec-carrosserie':'الهيكل',
      'spec-km':         'الكيلومتراج',
      'spec-etat':       'الحالة',
      'spec-couleur':    'اللون',
      'spec-places':     'المقاعد',
      'spec-carburant':  'الوقود',
      'spec-cylindree':  'الحجم',
      'spec-transmission':'نظام الدفع',
      'spec-dispo':      'التوفر',
      'sec-motorisation':'المحرك',
      'spec-moteur':     'المحرك',
      'spec-puissance':  'القوة',
      'spec-couple':     'عزم الدوران',
      'spec-boite':      'ناقل الحركة',
      'spec-traction':   'نظام الدفع',
      'spec-0100':       '0–100 كم/س',
      'spec-vmax':       'السرعة القصوى',
      'spec-conso':      'الاستهلاك',
      'sec-equip':       'التجهيزات والتكنولوجيا',
      'sec-confort':     'الراحة والخيارات',
      'sec-securite':    'الأمان',
      'gallery-label':   'معرض الصور',
      'gallery-title':   'جميع الصور',
      'cta-wa':          'تواصل معنا عبر واتساب',
      'cta-back':        'مشاهدة سيارات أخرى',
      'footer-tag':      'معرض فاخر — الشراقة، الجزائر',
      'footer-copy':     '© 2026 Kinan Cars. جميع الحقوق محفوظة.',
      'occasion-txt':    'مستعمل',
      'neuf-txt':        'جديد',
      'dispo-txt':       'فوري',
    }
  };

  function applyLang(lang) {
    var t = UI[lang] || UI.fr;
    var html = document.documentElement;
    html.lang = lang;
    html.classList.toggle('ar', lang === 'ar');
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.dataset.i18n;
      if (t[key] !== undefined) el.innerHTML = t[key];
    });
    var btn = document.getElementById('langBtn');
    if (btn) btn.innerHTML = lang === 'ar' ? '<b>عر</b> | FR' : 'FR | <b>عر</b>';
    localStorage.setItem('lang', lang);
  }

  window.toggleLang = function () {
    applyLang((localStorage.getItem('lang') || 'fr') === 'fr' ? 'ar' : 'fr');
  };

  applyLang(localStorage.getItem('lang') || 'fr');
})();
