"""Public website copy, taken word for word from the old Next.js components.

Header, footer and home-page sections have Thai and English versions (the old
site had a TH/EN switch for these). Inner pages were Thai-only in the old site
and stay that way here.
"""

NAV = [
    ('home', 'website:home'),
    ('about', 'website:about'),
    ('services', 'website:services'),
    ('authProcess', 'website:process'),
    ('certVerify', 'website:verify'),
    ('partner', 'website:partner'),
    ('contact', 'website:contact'),
]

COMMON = {
    'en': {
        'home': 'Home', 'about': 'About', 'services': 'Services', 'authProcess': 'Authentication Process',
        'certVerify': 'Certificate Verify', 'partner': 'Partner Program', 'contact': 'Contact',
        'bookAuth': 'Book Authentication', 'memberPortal': 'Dashboard', 'login': 'Login',
        'verifyCert': 'Verify Certificate', 'becomePartner': 'Become a Partner',
        'tagline': 'VERIFY · INSPECT · ASSURE', 'companyTitle': 'COMPANY', 'aboutUs': 'About TRUST LAB',
        'contactUs': 'Contact Us', 'servicesTitle': 'SERVICES', 'authService': 'Authentication Service',
        'authCert': 'Authentication Certificate', 'certVerification': 'Certificate Verification',
        'membershipProg': 'Membership Program', 'contactTitle': 'CONTACT US', 'phoneVal': '0640678666',
        'emailVal': 'trustlabthailand@gmail.com',
        'addressVal': 'TRUST LAB THAILAND Unit MS1107, Floor 1 Siam Square One 388 Rama I Road Pathum Wan, '
                      'Bangkok 10330 Thailand',
        'disclaimer': 'TRUST LAB THAILAND operates as an independent third-party luxury authentication laboratory. '
                      'We are not affiliated with, endorsed by, sponsored by, or officially associated with any '
                      'luxury brand featured on this website. All trademarks, logos, and product names are the '
                      'property of their respective owners and are used solely for identification and '
                      'authentication purposes. Authentication conclusions are issued independently by TRUST LAB '
                      'THAILAND according to our professional inspection standards and authentication protocols.',
        'copyright': '© 2026 TRUST LAB THAILAND.', 'privacyPolicy': 'Privacy Policy',
        'termsConditions': 'Terms & Conditions',
    },
    'th': {
        'home': 'หน้าแรก', 'about': 'เกี่ยวกับเรา', 'services': 'บริการ', 'authProcess': 'กระบวนการตรวจสอบ',
        'certVerify': 'ตรวจสอบใบรับรอง', 'partner': 'โปรแกรมพาร์ทเนอร์', 'contact': 'ติดต่อเรา',
        'bookAuth': 'จองคิวตรวจสอบ', 'memberPortal': 'แดชบอร์ดสมาชิก', 'login': 'เข้าสู่ระบบ',
        'verifyCert': 'ตรวจสอบใบรับรอง', 'becomePartner': 'สมัครเป็นพาร์ทเนอร์',
        'tagline': 'VERIFY · INSPECT · ASSURE', 'companyTitle': 'บริษัท', 'aboutUs': 'เกี่ยวกับ TRUST LAB',
        'contactUs': 'ติดต่อเรา', 'servicesTitle': 'บริการ', 'authService': 'บริการตรวจสอบสินค้า',
        'authCert': 'ใบรับรองการตรวจสอบ', 'certVerification': 'ตรวจสอบใบรับรอง', 'membershipProg': 'สมาชิก TRUST LAB',
        'contactTitle': 'ติดต่อเรา', 'phoneVal': '0640678666', 'emailVal': 'trustlabthailand@gmail.com',
        'addressVal': 'TRUST LAB THAILAND ชั้น 1 ห้อง MS1107 ศูนย์การค้าสยามสแควร์วัน 388 ถนนพระราม 1 '
                      'แขวงปทุมวัน เขตปทุมวัน กรุงเทพมหานคร 10330 ประเทศไทย',
        'disclaimer': 'TRUST LAB THAILAND เป็นห้องปฏิบัติการตรวจสอบสินค้าแบรนด์เนมอิสระ (Independent Third-Party '
                      'Authentication Laboratory) โดยไม่มีความเกี่ยวข้อง ได้รับการรับรอง สนับสนุน หรือเป็นตัวแทนอย่าง'
                      'เป็นทางการของแบรนด์ใดที่ปรากฏบนเว็บไซต์นี้ เครื่องหมายการค้า โลโก้ และชื่อผลิตภัณฑ์ทั้งหมดเป็น'
                      'ทรัพย์สินของเจ้าของเครื่องหมายการค้านั้น ๆ และใช้เพื่อวัตถุประสงค์ในการระบุและตรวจสอบสินค้าเท่านั้น '
                      'ผลการตรวจสอบทั้งหมดจัดทำขึ้นโดย TRUST LAB THAILAND ตามมาตรฐานการตรวจสอบและกระบวนการวิเคราะห์'
                      'ของห้องปฏิบัติการอย่างเป็นอิสระ',
        'copyright': '© 2569 TRUST LAB THAILAND. สงวนลิขสิทธิ์', 'privacyPolicy': 'นโยบายความเป็นส่วนตัว',
        'termsConditions': 'ข้อกำหนดและเงื่อนไข',
    },
}

HERO_IMAGES = ['img/images/hero/hero-01.jpg', 'img/images/hero/hero-02.jpg',
               'img/images/hero/hero-03.jpg', 'img/images/hero/hero-04.jpg']

STEP_ICONS = ['hi-shopping-bag', 'hi-search', 'hi-shield-check', 'hi-document-text', 'hi-cube']

HOME = {
    'en': {
        'eyebrow': 'PROFESSIONAL LUXURY AUTHENTICATION LABORATORY',
        'slides': [
            'Every luxury item is inspected by internationally experienced authentication specialists through a '
            'professional, transparent, and reliable authentication process.',
            'Every inspection follows a standardized process with over 100 authentication checkpoints to ensure '
            'consistent and reliable results.',
            'Receive an Authentication Certificate with a unique Certificate ID and QR Code for online verification '
            'and traceability.',
            'Precision Beyond the Naked Eye. Our international authentication specialists utilize high-magnification '
            'microscopes and professional inspection equipment to examine details invisible to the naked eye',
        ],
        'whyHeading': 'Why TRUST LAB',
        'whySub': 'Every authentication follows internationally recognized standards, ensuring accurate, '
                  'transparent, and reliable results.',
        'features': [
            ('hi-badge-check', 'International Experts', 'Every item is examined by internationally experienced '
             'authentication specialists with over 10 years of expertise in luxury authentication.'),
            ('hi-clipboard-check', '100+ Authentication Checkpoints', 'Every authentication follows a standardized '
             'process with over 100 inspection checkpoints for accurate and consistent results.'),
            ('hi-zoom-in', 'Advanced Equipment', 'High-magnification microscopes and professional inspection '
             'equipment reveal details beyond the naked eye.'),
            ('hi-shield-check', 'Fast & Reliable Service', 'Receive authentication results within 15–30 minutes, '
             'along with an Authentication Certificate and online QR verification.'),
        ],
        'cpHeadline': '100+ AUTHENTICATION<br>CHECKPOINTS',
        'cpSub': 'Verified by Experts. Assured by Science.',
        'cpDesc': 'TRUST LAB’s authentication protocol includes over 100 authentication checkpoints, with inspection '
                  'criteria tailored to each brand, model, product category, and production period to ensure '
                  'accurate, transparent, and reliable authentication results.',
        'cpButton': 'VIEW ALL INSPECTION CATEGORIES',
        'cpCards': [
            ('hi-document', 'material', 'MATERIAL & LEATHER', 'Examine the leather structure, texture, softness, '
             'smell, and overall weight of the material in detail.'),
            ('hi-lock', 'hardware', 'HARDWARE', 'Verify metals, zippers, engravings, weight, shine, and depth of '
             'brand engravings.'),
            ('hi-menu-alt', 'interior', 'INTERIOR', 'Inspect lining fabric, inner stamp stamps, pocket layout, and '
             'stitching alignment carefully.'),
            ('hi-document-text', 'serial', 'SERIAL & AUTHENTICITY', 'Check date code stickers, serial numbers, '
             'holograms, and brand-specific font typography.'),
            ('hi-zoom-in', 'advanced', 'ADVANCED INSPECTION', 'Analyze fibers, needle holes, adhesive residues, and '
             'RFID/NFC chips under high microscopic magnification.'),
        ],
        'processHeading': 'AUTHENTICATION PROCESS',
        'processSub': 'Our transparent 5-step authentication process explained for your peace of mind.',
        'steps': [
            ('SUBMIT ITEM', 'Submit Item', 'Bring your item to our laboratory or send it by delivery.'),
            ('INSPECTION', 'Inspection', 'Detailed inspection through over 100 authentication checkpoints by our '
             'specialists.'),
            ('AUTHENTICATION', 'Authentication', 'Our specialists analyze the inspection results and confirm the '
             'final authentication outcome.'),
            ('CERTIFICATE', 'Certificate', 'Issue an Authentication Certificate with Certificate ID, QR Code, and '
             'digital inspection record.'),
            ('RETURN ITEM', 'Return Item', 'Return your item securely with appropriate protective packaging.'),
        ],
        'brandsTitle': 'BRANDS WE AUTHENTICATE', 'brandsSub': 'Search the luxury brands we can authenticate.',
        'searchPlaceholder': 'Search brands…', 'viewAllBrands': 'VIEW ALL BRANDS',
        'noBrandsFound': 'No brands found matching your search.',
        'productsTitle': 'PRODUCTS WE AUTHENTICATE',
        'productsSub': 'Luxury product categories we authenticate in our laboratory.',
        'viewAllCategories': 'VIEW ALL CATEGORIES',
        'products': [
            ('hi-shopping-bag', 'Bag', ''), ('hi-card', 'Wallets', '& SMALL LEATHER GOODS'), ('hi-watch', 'watch', ''),
            ('hi-badge-check', 'Accessories', ''), ('hi-sunglasses', 'Sunglasses', ''), ('hi-sneaker', 'Shoes', ''),
            ('hi-apparel', 'Clothes', ''), ('hi-luggage', 'Luggage', ''),
        ],
    },
    'th': {
        'eyebrow': 'ห้องปฏิบัติการตรวจสอบสินค้าแบรนด์เนมระดับมืออาชีพ',
        'slides': [
            'ทุกชิ้นงานได้รับการตรวจสอบโดยผู้เชี่ยวชาญระดับสากล ผ่านกระบวนการตรวจสอบที่เป็นมาตรฐาน โปร่งใส และเชื่อถือได้',
            'ทุกชิ้นผ่านมาตรฐานการตรวจสอบกว่า 100 จุด เพื่อผลการตรวจที่แม่นยำ และน่าเชื่อถือ',
            'รับใบรับรองการตรวจสอบ พร้อม Certificate ID และ QR Code สำหรับยืนยันและตรวจสอบผลการตรวจออนไลน์',
            'แม่นยำในรายละเอียดที่ตามองไม่เห็น ผู้เชี่ยวชาญระดับสากลใช้อุปกรณ์ตรวจสอบเฉพาะทางและกล้องไมโครสโคปกำลังขยายสูง '
            'เพื่อวิเคราะห์รายละเอียดสำคัญของสินค้าอย่างแม่นยำ',
        ],
        'whyHeading': 'ทำไมต้อง TRUST LAB',
        'whySub': 'ทุกขั้นตอนของการตรวจสอบดำเนินการตามมาตรฐานระดับสากล เพื่อผลการตรวจที่แม่นยำ โปร่งใส และเชื่อถือได้',
        'features': [
            ('hi-badge-check', 'ผู้เชี่ยวชาญระดับสากล', 'สินค้าทุกชิ้นได้รับการตรวจสอบโดยผู้เชี่ยวชาญด้านการตรวจสอบสินค้าแบรนด์เนม '
             'ที่มีประสบการณ์มากกว่า 10 ปี และผ่านการฝึกอบรมตามมาตรฐานระดับสากล'),
            ('hi-clipboard-check', 'มาตรฐานการตรวจสอบกว่า 100 จุด', 'ทุกชิ้นผ่านกระบวนการตรวจสอบมากกว่า 100 จุด '
             'ครอบคลุมรายละเอียดสำคัญของสินค้า เพื่อผลการตรวจที่แม่นยำและเป็นมาตรฐานเดียวกัน'),
            ('hi-zoom-in', 'เทคโนโลยีการตรวจสอบระดับมืออาชีพ', 'ใช้อุปกรณ์ตรวจสอบเฉพาะทางและกล้องไมโครสโคปกำลังขยายสูง '
             'เพื่อวิเคราะห์รายละเอียดที่ไม่สามารถมองเห็นได้ด้วยตาเปล่า'),
            ('hi-shield-check', 'รวดเร็ว แม่นยำ และเชื่อถือได้', 'ทราบผลการตรวจภายใน 15–30 นาที พร้อมใบรับรองการตรวจสอบ '
             '(Authentication Certificate) และระบบตรวจสอบผลออนไลน์ผ่าน Certificate ID และ QR Code'),
        ],
        'cpHeadline': '100+ จุดตรวจสอบมาตรฐาน',
        'cpSub': 'ตรวจสอบโดยผู้เชี่ยวชาญ ด้วยมาตรฐานระดับห้องปฏิบัติการ',
        'cpDesc': 'ระบบการตรวจสอบของ TRUST LAB ครอบคลุมมากกว่า 100 จุดตรวจสอบ โดยใช้เกณฑ์การตรวจสอบที่ปรับให้เหมาะสมตาม '
                  'แบรนด์ รุ่น ประเภทสินค้า และช่วงการผลิต เพื่อมอบผลการตรวจสอบที่แม่นยำ และเชื่อถือได้',
        'cpButton': 'ดูมาตรฐานการตรวจสอบทั้งหมด',
        'cpCards': [
            ('hi-document', 'material', 'วัสดุและหนัง', 'ตรวจสอบโครงสร้างและคุณสมบัติของหนัง ความนุ่ม กลิ่น และน้ำหนักอย่างละเอียด'),
            ('hi-lock', 'hardware', 'ฮาร์ดแวร์', 'ตรวจสอบโลหะ อะไหล่ ซิป ตราประทับ น้ำหนัก ความเงา และความลึกของสลักแบรนด์'),
            ('hi-menu-alt', 'interior', 'ภายในและโครงสร้าง', 'ตรวจสอบผ้าบุ ซับใน ตราแสตมป์ การจัดแบ่งสัดส่วนกระเป๋าด้านในอย่างรอบคอบ'),
            ('hi-document-text', 'serial', 'ซีเรียลและการระบุอัตลักษณ์', 'ตรวจสอบสติกเกอร์รหัสปี เลขซีเรียล แผ่นโฮโลแกรม และแบบอักษรฟอนต์ประจำปี'),
            ('hi-zoom-in', 'advanced', 'การตรวจสอบทางวิทยาศาสตร์ขั้นสูง', 'สแกนระดับไมโครสโคป วิเคราะห์เส้นใยด้าย รูเข็ม คราบกาว และแผ่นชิป RFID/NFC'),
        ],
        'processHeading': 'ขั้นตอนการตรวจสอบ',
        'processSub': 'อธิบายขั้นตอนการตรวจสอบสินค้า 5 ขั้นตอนให้คุณเข้าใจอย่างโปร่งใสก่อนส่งมอบ',
        'steps': [
            ('SUBMIT ITEM', 'ส่งสินค้าตรวจสอบ', 'ส่งทางไปรษณีย์ หรือเดินทางมาส่งด้วยตนเองที่สาขา'),
            ('INSPECTION', 'ตรวจสอบสินค้า', 'ผู้เชี่ยวชาญตรวจสอบสินค้าผ่านมาตรฐานการตรวจสอบกว่า 100 จุด อย่างละเอียดในทุกองค์ประกอบสำคัญ'),
            ('AUTHENTICATION', 'สรุปผลการตรวจสอบ', 'ผู้เชี่ยวชาญวิเคราะห์ผลการตรวจสอบ และยืนยันผลการตรวจสอบอย่างเป็นทางการ'),
            ('CERTIFICATE', 'ออกใบรับรอง', 'ออกใบรับรองการตรวจสอบ พร้อม Certificate ID, QR Code และบันทึกผลการตรวจสอบในระบบออนไลน์'),
            ('RETURN ITEM', 'ส่งคืนสินค้า', 'บรรจุและจัดส่งสินค้าคืนอย่างปลอดภัย ด้วยมาตรฐานการดูแลของ TRUST LAB'),
        ],
        'brandsTitle': 'แบรนด์ที่ให้บริการตรวจสอบ', 'brandsSub': 'เสิร์ชแบรนด์หรูที่เราสามารถให้การตรวจสอบได้อย่างเป็นสากล',
        'searchPlaceholder': 'ค้นหาแบรนด์…', 'viewAllBrands': 'ดูแบรนด์ทั้งหมด', 'noBrandsFound': 'ไม่พบแบรนด์ที่คุณค้นหา',
        'productsTitle': 'ประเภทสินค้าที่ให้บริการตรวจสอบ', 'productsSub': 'ประเภทสินค้าลักชัวรีที่พร้อมให้บริการ',
        'viewAllCategories': 'ดูหมวดหมู่ทั้งหมด',
        'products': [
            ('hi-shopping-bag', 'กระเป๋า', ''), ('hi-card', 'กระเป๋าสตางค์', '& สินค้าเครื่องหนังขนาดเล็ก'),
            ('hi-watch', 'นาฬิกา', ''), ('hi-badge-check', 'เครื่องประดับ', ''), ('hi-sunglasses', 'แว่นตากันแดด', ''),
            ('hi-sneaker', 'รองเท้า', ''), ('hi-apparel', 'เสื้อผ้า', ''), ('hi-luggage', 'กระเป๋าเดินทาง', ''),
        ],
    },
}

HOME_BRANDS = ['Chanel', 'Louis Vuitton', 'Hermès', 'Dior', 'Gucci', 'Prada', 'Celine', 'Saint Laurent',
               'Bottega Veneta', 'Miu Miu', 'Loewe', 'Fendi', 'Goyard', 'Balenciaga', 'Rimowa', 'Burberry',
               'Valentino', "Tod's", 'Chloé']

TRUSTEE_PARTNERS = [
    ('hi-switch', 'BUY / SELL STORES', 'ร้านรับซื้อ-ขายสินค้าแบรนด์เนม'),
    ('hi-collection', 'CONSIGNMENT STORES', 'ร้านฝากขายสินค้าแบรนด์เนม'),
    ('hi-globe', 'LUXURY BOUTIQUES', 'ตัวแทนจำหน่ายสินค้าหรูหรา'),
    ('hi-scale', 'AUCTION HOUSES', 'บริษัทประมูลสินค้าแบรนด์เนม'),
    ('hi-desktop', 'ONLINE PLATFORMS', 'แพลตฟอร์มตลาดออนไลน์'),
]

ABOUT_VALUES = [
    ('hi-badge-check', 'INTEGRITY', 'ความซื่อสัตย์เป็นธรรม', 'เราทำหน้าที่เป็นหน่วยงานตรวจสอบอิสระที่มีความเป็นกลางสูงสุด '
     'ไม่ยุ่งเกี่ยวกับการซื้อขาย ทำให้ผลตรวจมีความยุติธรรมและไร้ผลประโยชน์ทับซ้อน'),
    ('hi-clipboard-check', 'PRECISION', 'ความแม่นยำขั้นสูง', 'การตรวจสอบทุกชิ้นงานต้องครอบคลุมมากกว่า 100 จุดตรวจสอบ '
     '(Checkpoints) ทั้งรอยเย็บ ด้าย โครงสร้าง ฮาร์ดแวร์ ตลอดจนแผ่นชิปเทคโนโลยี'),
    ('hi-zoom-in', 'ADVANCED SCIENCE', 'เทคโนโลยีและเครื่องมือวิทยาศาสตร์', 'เราผสานความสามารถของผู้เชี่ยวชาญร่วมกับเครื่องมือ'
     'ระดับห้องวิจัยวิทยาศาสตร์ เช่น กล้องจุลทรรศน์อิเล็กทรอนิกส์ และเครื่องตรวจจับคลื่นแม่เหล็กไฟฟ้า'),
    ('hi-shield-check', 'TRUST SECURED', 'ระบบใบเซอร์ยืนยันความปลอดภัย', 'รหัสและ QR Code ใบรับรองผลของเราสามารถตรวจสอบ'
     'ออนไลน์แบบเรียลไทม์ได้ตลอด 24 ชั่วโมง พร้อมระบบป้องกันการปลอมแปลงและลายน้ำใบเซอร์พิเศษ'),
]

SERVICE_PACKAGES = [
    {'name': 'PHOTO REVIEW ONLY', 'label': 'ตรวจจากรูป', 'price': 'เริ่มต้น ฿500', 'unit': 'ต่อชิ้นงาน',
     'description': 'เหมาะสำหรับกรณีต้องการทราบผลเบื้องต้นอย่างรวดเร็วจากรูปถ่ายสินค้าที่ส่งมา',
     'features': ['ตรวจสอบเบื้องต้นโดยผู้เชี่ยวชาญผ่านรูปถ่าย', 'ทราบผลการตรวจสอบรวดเร็ว',
                  'ระบุผล Authentic / Counterfeit / Inconclusive ชัดเจน',
                  'ต้องถ่ายภาพตามจุดตรวจที่กำหนดอย่างครบถ้วนและคมชัด',
                  'ไม่สามารถออกใบรับรองและ QR Code ตรวจสอบออนไลน์ได้'],
     'cta': 'จองตรวจจากรูป', 'url': 'website:booking', 'popular': False},
    {'name': 'AUTHENTICATION & CERTIFICATE', 'label': 'ตรวจสินค้าพร้อมใบรับรอง', 'price': 'เริ่มต้น ฿1,000',
     'unit': 'ต่อชิ้นงาน',
     'description': 'บริการมาตรฐานสูงสุด ตรวจสินค้าตัวจริงในห้องปฏิบัติการ 100+ จุดตรวจ พร้อมออกใบรับรองยืนยันออนไลน์',
     'features': ['ตรวจสินค้าชิ้นจริงโดยคณะกรรมการผู้เชี่ยวชาญ',
                  'ตรวจสอบระดับไมโครสโคป วิเคราะห์เส้นใย อะไหล่ และ Date Code',
                  'ออกเลขรหัส Certificate ID ออนไลน์ของ TRUST LAB',
                  'เลือกอายุใบรับรองได้ 15 วัน (฿1,000) หรือ 90 วัน (฿3,000)',
                  'สแกน QR Code ตรวจสอบออนไลน์ได้จริงตลอดอายุใบรับรอง',
                  'ดาวน์โหลดใบรับรองฉบับเต็ม PDF พร้อมแท็กรับรองของแท้'],
     'cta': 'จองตรวจพร้อมใบรับรอง', 'url': 'website:booking', 'popular': True},
    {'name': 'ENTERPRISE & PARTNERSHIP', 'label': 'สิทธิพิเศษสำหรับ พาร์ทเนอร์และร้านค้า', 'price': 'ติดต่อสอบถาม',
     'unit': 'แพ็กเกจเครดิตร้านค้า', 'description': 'เหมาะสำหรับร้านค้าแบรนด์เนม ร้านรับซื้อ ฝากขาย หรือโรงประมูลชั้นนำ',
     'features': ['อัตราค่าบริการพิเศษแบบหักเครดิตสะสมในบัญชี', 'ระบบหลังบ้านจัดการงานตรวจและประวัติลูกค้าของร้าน',
                  'ระบบหักยอดเครดิตส่งงานตรวจผ่านเบอร์โทรศัพท์ร้านค้า', 'ช่องทางส่งตรวจพิเศษแบบ Fast Track ด่วนพิเศษ',
                  'สรุปรายงานประจำเดือนสำหรับออกเอกสารบัญชีได้ง่าย'],
     'cta': 'สมัครโปรแกรมพาร์ทเนอร์', 'url': 'website:partner', 'popular': False},
]

SERVICE_CATEGORIES = [
    ('HANDBAGS', 'กระเป๋าถือ กระเป๋าสะพาย และคลัตช์หรูหรา'),
    ('WALLETS & SLG', 'กระเป๋าสตางค์ เคสการ์ด และสินค้าหนังชิ้นเล็ก'),
    ('WATCHES', 'นาฬิกาแบรนด์หรู และระบบกลไกกล่องใบครบ'),
    ('JEWELRY', 'เครื่องประดับล้ำค่า ทองคำขาว เพชรพลอย และแสตมป์โลหะ'),
    ('SUNGLASSES', 'แว่นตากันแดด โครงเหล็ก และฟอนต์ขาแว่น'),
    ('SNEAKERS', 'รองเท้าสนีกเกอร์ลิมิเต็ด ด้ายเย็บ และแผ่นพื้นกันกระแทก'),
    ('APPAREL', 'เสื้อผ้าแจ็คเก็ต เครื่องแต่งกาย และป้ายคอเสื้อ'),
    ('LUGGAGE', 'กระเป๋าเดินทางล้อลาก ตัวล็อกสลัก และโครงกระเป๋า'),
]

LAB_TOOLS = [
    ('hi-eye', 'DIGITAL STEREO MICROSCOPE', 'กล้องจุลทรรศน์สเตอริโอดิจิทัล',
     'ขยายรายละเอียดรูข็ม สภาพเส้นใยหนัง และคราบกาวรอยต่อได้สูงถึง 1000 เท่า ทำให้จับผิดฝีเข็มของปลอมได้ทันที'),
    ('hi-sun', 'ULTRAVIOLET LIGHT SCANNER', 'เครื่องสแกนแสงอัลตราไวโอเลต',
     'ตรวจสอบสารเรืองแสงและรอยพิมพ์เคมีพิเศษบนการ์ดแฮงแท็ก รวมถึงตราแสตมป์หมึกสะท้อนแสงเฉพาะจุดที่ไม่เห็นในแสงธรรมชาติ'),
    ('hi-finger-print', 'NFC & RFID SIGNAL ANALYSER', 'เครื่องวิเคราะห์สัญญาณคลื่นวิทยุชิป',
     'อ่านข้อมูลจากแผ่นชิปที่ฝังภายในกระเป๋าแบรนด์เนมรุ่นใหม่ๆ (เช่น Chanel / LV รุ่นปีล่าสุด) '
     'เพื่อเทียบกับชุดความรหัสลับจากฐานข้อมูลผู้ผลิต'),
]

CHECKPOINT_BOXES = [
    ('1. MATERIAL & STITCHING (หนังและรอยเย็บ)', [
        ('การวิเคราะห์โครงสร้างเส้นใยหนัง', 'ตรวจสอบความอ่อนนุ่ม ความตึง และกลิ่นหนังเฉพาะตัวของผู้ผลิตแต่ละแบรนด์'),
        ('ฝีเข็มและด้ายเย็บ', 'ตรวจสอบมุมการแทงเข็ม ความถี่ในการเย็บด้าย (Stitch count per inch) และสีของด้ายเย็บในแต่ละรุ่นปี'),
        ('ขอบสีและน้ำยาขอบหนัง', 'เช็คความสมดุลและความเรียบร้อยในการลงสีขอบของกระเป๋า'),
    ]),
    ('2. HARDWARE & ENGRAVING (ฮาร์ดแวร์และการสลักลาย)', [
        ('ฟอนต์การสลักตราแบรนด์', 'ตรวจเช็คความลึก ความกว้าง และแบบฟอนต์อักษรของการปั๊มทองเหลือง อลูมิเนียม หรือสแตนเลส'),
        ('น้ำหนักฮาร์ดแวร์โลหะ', 'ชั่งน้ำหนักฮาร์ดแวร์แต่ละชิ้นด้วยตาชั่งดิจิทัลจุดทศนิยม 2 ตำแหน่งเทียบข้อมูลสเปกโรงงาน'),
        ('ความเรียบและรอยเกลียวซิป', 'ตรวจสอบรอยปั๊มโลโก้ที่หัวซิปและฟันซิปของแบรนด์ชั้นนำ (เช่น YKK, riri, Lampo)'),
    ]),
]

CONTACT_INFO = [
    ('hi-location', 'ADDRESS', 'BKK - Siam Square One',
     'TRUST LAB THAILAND ชั้น 1 ห้อง MS1107 ศูนย์การค้าสยามสแควร์วัน 388 ถนนพระราม 1 แขวงปทุมวัน เขตปทุมวัน กรุงเทพมหานคร 10330'),
    ('hi-phone', 'PHONE', 'ฝ่ายบริการลูกค้าสัมพันธ์', '064-067-8666 | trustlabthailand@gmail.com'),
    ('hi-chat', 'ONLINE CHAT & Hours', 'LINE & เวลาเปิดทำการ', 'LINE Official: lin.ee/QqbYaFE | เปิดบริการทุกวัน 11:30 - 20:30 น.'),
]

PARTNER_BENEFITS = [
    ('hi-lightning', 'FAST TRACK AUTHENTICATION', 'บริการด่วนพิเศษสำหรับหน้าร้าน',
     'ลดระยะเวลารอคอย ทราบผลการตรวจสอบระดับความถูกต้อง 100% ภายใน 3-6 ชั่วโมง ช่วยให้ปิดดีลหน้าร้านรับซื้อ-ขาย'
     'สินค้าแบรนด์เนมได้ทันที'),
    ('hi-currency', 'DISCOUNTED CREDIT RATE', 'อัตราค่าส่งตรวจพิเศษแบบสะสมคะแนน',
     'ประหยัดต้นทุนค่าส่งตรวจสูงสุด 30% ด้วยระบบสมาชิกหักยอดเครดิตสะสมในระบบ ยิ่งส่งตรวจบ่อยยิ่งได้เรตส่วนลดที่สูงขึ้นตามระดับ Tier'),
    ('hi-view-grid', 'STORE DASHBOARD ACCESS', 'แดชบอร์ดจัดการงานตรวจของร้านค้า',
     'แดชบอร์ดเฉพาะร้านค้าของคุณเพื่อตรวจสอบรหัสคิว, ค้นหาใบเซอร์ย้อนหลัง และส่งใบเซอร์ออนไลน์ให้แก่ลูกค้าผู้เช่าซื้อของคุณได้อย่างโปร่งใส'),
]

CATEGORY_LABELS = {
    'Bag': ('กระเป๋า', 'Bag', 'hi-shopping-bag'),
    'Watch': ('นาฬิกา', 'Watch', 'hi-watch'),
    'Shoes': ('รองเท้า', 'Shoes', 'hi-sneaker'),
    'Clothes': ('เสื้อผ้า', 'Clothes', 'hi-apparel'),
    'Accessories': ('เครื่องประดับ/แอคเซสซอรี่', 'Accessories', 'hi-badge-check'),
}

DEFAULT_BRANDS = HOME_BRANDS


def copy_for(lang: str, *pages) -> dict:
    """Merge COMMON with page dictionaries for the given language."""
    merged = dict(COMMON.get(lang, COMMON['en']))
    for page in pages:
        merged.update(page.get(lang, page['en']))
    return merged


BOOKING_STEPS = ['1. เลือกสาขา', '2. เลือกบริการ', '3. ข้อมูลติดต่อ', '4. รายละเอียดสินค้า', '5. แนบรูปถ่ายสินค้า',
                 '6. เลือกวันและเวลา', '7. สรุปและชำระเงิน']
BOOKING_SLOTS = ['11:30-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00',
                 '18:00-19:00', '19:00-20:30']
CATEGORY_BRANDS = {
    'Bag': ['Hermes', 'Chanel', 'Delvaux', 'Dior', 'Miu Miu', 'Celine', 'Loewe', 'Goyard', 'Bvlgari', 'Gucci', 'Prada',
            'Fendi', 'Balenciaga', 'YSL', 'Bottega Veneta', 'Louis Vuitton', 'Chloe', 'MCM', 'Burberry', 'Moynat'],
    'Clothes': ['Louis Vuitton', 'Gucci', 'Burberry', 'Balenciaga', 'Loewe', 'Hermes', 'Chanel', 'Dior', 'Prada',
                'Miu Miu', 'Fendi', 'Celine', 'YSL', 'Max Mara', 'Canada Goose', 'Moncler'],
    'Shoes': ['Louis Vuitton', 'Gucci', 'Burberry', 'Balenciaga', 'Loewe', 'Hermes', 'Chanel', 'Dior', 'Prada', 'Miu Miu',
              'Fendi', 'Celine', 'YSL', 'Max Mara', 'Canada Goose', 'Moncler'],
    'Accessories': ['Harry Winston', 'Graff', 'Buccellati', 'Chaumet', 'Van Cleef & Arpels', 'Boucheron', 'Piaget',
                    'Qeelin', 'Cartier', 'Bvlgari', 'Chopard', 'Tiffany & Co.', 'Chanel', 'Hermes', 'Dior',
                    'Louis Vuitton', 'Gucci'],
    'Watch': ['Patek Philippe Genève', 'A. Lange & Söhne', 'Vacheron Constantin', 'Roger Dubuis', 'Audemars Piguet',
              'Richard Mille', 'Blancpain', 'Breguet', 'Rolex', 'Jaeger-LeCoultre', 'Girard-Perregaux',
              'Van Cleef & Arpels', 'Piaget', 'Glashütte Original', 'Cartier', 'Omega', 'IWC Schaffhausen', 'Breitling',
              'Hublot', 'Panerai', 'Zenith', 'Chopard', 'Franck Muller', 'Longines', 'Tudor', 'Chanel', 'Hermes'],
}
THAI_PROVINCES = [
    'กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท',
    'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา',
    'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์',
    'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พะเยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์',
    'แพร่', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยโสธร', 'ยะลา', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี',
    'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร',
    'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู',
    'อ่างทอง', 'อำนาจเจริญ', 'อุดรธานี', 'อุตรดิตถ์', 'อุทัยธานี', 'อุบลราชธานี',
]
