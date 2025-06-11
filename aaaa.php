<?php
session_start();

// إعدادات قاعدة البيانات
$config = [
    'host' => 'localhost',
    'dbname' => 'portfolio_db',
    'username' => 'root',
    'password' => '',
    'charset' => 'utf8mb4'
];

// الاتصال بقاعدة البيانات
$pdo = null;
try {
    $dsn = "mysql:host={$config['host']};dbname={$config['dbname']};charset={$config['charset']}";
    $pdo = new PDO($dsn, $config['username'], $config['password']);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch(PDOException $e) {
    error_log("Database connection failed: " . $e->getMessage());
}

// بيانات المقالات التقنية
$articles = [
    [
        'id' => 1,
        'title' => 'أفضل ممارسات تطوير المواقع الحديثة',
        'excerpt' => 'تعرف على أحدث التقنيات والأساليب المتبعة في تطوير المواقع الاحترافية',
        'content' => 'في عالم تطوير الويب المتطور، هناك عدة ممارسات يجب اتباعها لضمان إنشاء مواقع عالية الجودة...',
        'category' => 'تطوير',
        'date' => '2024-12-01',
        'image' => 'https://via.placeholder.com/400x250/667eea/ffffff?text=تطوير+المواقع',
        'tags' => ['PHP', 'JavaScript', 'CSS']
    ],
    [
        'id' => 2,
        'title' => 'أهمية تحسين الأداء في المواقع الإلكترونية',
        'excerpt' => 'كيفية تحسين سرعة وأداء موقعك الإلكتروني لتجربة مستخدم أفضل',
        'content' => 'سرعة تحميل الموقع عامل حاسم في نجاح أي موقع إلكتروني. سنتعرف على الطرق الفعالة...',
        'category' => 'تحسين',
        'date' => '2024-11-28',
        'image' => 'https://via.placeholder.com/400x250/764ba2/ffffff?text=تحسين+الأداء',
        'tags' => ['Performance', 'SEO', 'Optimization']
    ],
    [
        'id' => 3,
        'title' => 'الأمان في تطبيقات الويب',
        'excerpt' => 'استراتيجيات وأساليب حماية تطبيقات الويب من التهديدات الأمنية',
        'content' => 'أمان التطبيقات الإلكترونية أولوية قصوى في عصرنا الحالي. سنستعرض أهم المخاطر وطرق الحماية...',
        'category' => 'أمان',
        'date' => '2024-11-25',
        'image' => 'https://via.placeholder.com/400x250/ff6b6b/ffffff?text=الأمان+الرقمي',
        'tags' => ['Security', 'Encryption', 'Protection']
    ]
];

// بيانات التطبيقات والأدوات
$applications = [
    [
        'id' => 1,
        'name' => 'منشئ الكلمات المرورية',
        'description' => 'أداة لإنشاء كلمات مرور قوية وآمنة',
        'icon' => '🔐',
        'features' => ['طول قابل للتخصيص', 'رموز خاصة', 'نسخ سريع'],
        'demo_url' => '#password-generator'
    ],
    [
        'id' => 2,
        'name' => 'محول الألوان',
        'description' => 'تحويل بين أنظمة الألوان المختلفة (HEX, RGB, HSL)',
        'icon' => '🎨',
        'features' => ['HEX إلى RGB', 'RGB إلى HSL', 'معاينة مباشرة'],
        'demo_url' => '#color-converter'
    ],
    [
        'id' => 3,
        'name' => 'مولد QR Code',
        'description' => 'إنشاء رموز QR للنصوص والروابط',
        'icon' => '📱',
        'features' => ['نص وروابط', 'أحجام مختلفة', 'تحميل مباشر'],
        'demo_url' => '#qr-generator'
    ],
    [
        'id' => 4,
        'name' => 'حاسبة المطور',
        'description' => 'حاسبة متقدمة للمطورين مع وظائف برمجية',
        'icon' => '🧮',
        'features' => ['عمليات برمجية', 'تحويل أنظمة العد', 'حفظ التاريخ'],
        'demo_url' => '#developer-calculator'
    ]
];

// معالجة النماذج
$messages = [];
$newsletter_message = '';

// معالجة نموذج التواصل
if ($_POST && isset($_POST['contact_form'])) {
    $name = htmlspecialchars(trim($_POST['name'] ?? ''));
    $email = htmlspecialchars(trim($_POST['email'] ?? ''));
    $subject = htmlspecialchars(trim($_POST['subject'] ?? ''));
    $message = htmlspecialchars(trim($_POST['message'] ?? ''));
    
    if ($name && $email && $subject && $message) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("INSERT INTO contact_messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, NOW())");
                $stmt->execute([$name, $email, $subject, $message]);
                $messages['contact'] = "تم إرسال رسالتك بنجاح! سأرد عليك في أقرب وقت.";
            } catch(PDOException $e) {
                $messages['contact'] = "حدث خطأ في إرسال الرسالة. يرجى المحاولة مرة أخرى.";
            }
        } else {
            $data = date('Y-m-d H:i:s') . " | $name | $email | $subject | $message\n";
            file_put_contents('contact_messages.txt', $data, FILE_APPEND | LOCK_EX);
            $messages['contact'] = "تم إرسال رسالتك بنجاح!";
        }
    }
}

// معالجة نموذج النشرة البريدية
if ($_POST && isset($_POST['newsletter_form'])) {
    $email = htmlspecialchars(trim($_POST['newsletter_email'] ?? ''));
    
    if ($email && filter_var($email, FILTER_VALIDATE_EMAIL)) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("INSERT INTO newsletter_subscribers (email, subscribed_at) VALUES (?, NOW()) ON DUPLICATE KEY UPDATE subscribed_at = NOW()");
                $stmt->execute([$email]);
                $newsletter_message = "تم اشتراكك بنجاح في النشرة البريدية!";
            } catch(PDOException $e) {
                $newsletter_message = "حدث خطأ في الاشتراك.";
            }
        } else {
            $data = date('Y-m-d H:i:s') . " | $email\n";
            file_put_contents('newsletter_subscribers.txt', $data, FILE_APPEND | LOCK_EX);
            $newsletter_message = "تم اشتراكك بنجاح!";
        }
    }
}

// إحصائيات
$stats = [
    'projects' => 75,
    'clients' => 60,
    'experience' => 7,
    'articles' => count($articles)
];
?>
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مهندس مواقع محترف - تطوير وتصميم المواقع الإلكترونية</title>
    <meta name="description" content="مهندس مواقع محترف متخصص في تطوير المواقع الحديثة باستخدام أحدث التقنيات">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --accent: #ff6b6b;
            --success: #4ecdc4;
            --warning: #ffe66d;
            --dark: #2c3e50;
            --light: #f8f9fa;
            --white: #ffffff;
            --shadow: 0 10px 30px rgba(0,0,0,0.1);
            --shadow-lg: 0 20px 60px rgba(0,0,0,0.15);
            --gradient: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            --gradient-accent: linear-gradient(135deg, var(--accent) 0%, #ff5252 100%);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Cairo', sans-serif;
            line-height: 1.7;
            color: var(--dark);
            overflow-x: hidden;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Loading Screen */
        .loading-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--gradient);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            transition: opacity 0.5s ease;
        }

        .loading-content {
            text-align: center;
            color: white;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Header */
        header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            padding: 1rem 0;
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 1000;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
        }

        .header-scrolled {
            padding: 0.5rem 0;
            background: rgba(255, 255, 255, 0.98);
        }

        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 2rem;
            font-weight: 900;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .nav-links {
            display: flex;
            list-style: none;
            gap: 2.5rem;
            align-items: center;
        }

        .nav-links a {
            text-decoration: none;
            color: var(--dark);
            font-weight: 600;
            position: relative;
            transition: all 0.3s ease;
            padding: 0.5rem 0;
        }

        .nav-links a::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 0;
            height: 2px;
            background: var(--gradient);
            transition: width 0.3s ease;
        }

        .nav-links a:hover::after,
        .nav-links a.active::after {
            width: 100%;
        }

        .mobile-menu-btn {
            display: none;
            background: none;
            border: none;
            font-size: 1.5rem;
            color: var(--dark);
            cursor: pointer;
        }

        /* Hero Section */
        .hero {
            background: var(--gradient);
            color: white;
            padding: 180px 0 120px;
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 100" fill="rgba(255,255,255,0.1)"><polygon points="0,0 1000,100 1000,0"/></svg>') no-repeat center bottom;
            background-size: cover;
        }

        .hero-content {
            text-align: center;
            position: relative;
            z-index: 2;
        }

        .hero h1 {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 900;
            margin-bottom: 1.5rem;
            opacity: 0;
            animation: slideInUp 1s ease 0.5s forwards;
        }

        .hero-subtitle {
            font-size: clamp(1.1rem, 2.5vw, 1.4rem);
            margin-bottom: 2rem;
            opacity: 0.9;
            opacity: 0;
            animation: slideInUp 1s ease 0.7s forwards;
        }

        .hero-cta {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 2rem;
            opacity: 0;
            animation: slideInUp 1s ease 0.9s forwards;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 15px 30px;
            border: none;
            border-radius: 50px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1rem;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            transition: all 0.3s ease;
            transform: translate(-50%, -50%);
        }

        .btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .btn-primary {
            background: var(--accent);
            color: white;
        }

        .btn-secondary {
            background: transparent;
            color: white;
            border: 2px solid white;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }

        /* Floating Elements */
        .floating-shapes {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 1;
        }

        .shape {
            position: absolute;
            opacity: 0.1;
            animation: float 6s ease-in-out infinite;
        }

        .shape:nth-child(1) {
            top: 20%;
            left: 10%;
            width: 60px;
            height: 60px;
            background: white;
            border-radius: 50%;
            animation-delay: 0s;
        }

        .shape:nth-child(2) {
            top: 60%;
            right: 10%;
            width: 80px;
            height: 80px;
            background: white;
            transform: rotate(45deg);
            animation-delay: 2s;
        }

        .shape:nth-child(3) {
            bottom: 20%;
            left: 20%;
            width: 40px;
            height: 40px;
            background: white;
            clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
            animation-delay: 4s;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(180deg); }
        }

        /* Section Styles */
        .section {
            padding: 100px 0;
            position: relative;
        }

        .section:nth-child(even) {
            background: var(--light);
        }

        .section-header {
            text-align: center;
            margin-bottom: 5rem;
        }

        .section-title {
            font-size: clamp(2rem, 4vw, 3rem);
            font-weight: 700;
            color: var(--dark);
            margin-bottom: 1rem;
            position: relative;
            display: inline-block;
        }

        .section-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 4px;
            background: var(--gradient);
            border-radius: 2px;
        }

        .section-subtitle {
            font-size: 1.2rem;
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }

        /* About Section */
        .about-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5rem;
            align-items: center;
            margin-bottom: 5rem;
        }

        .about-text {
            font-size: 1.1rem;
            line-height: 1.8;
        }

        .about-text p {
            margin-bottom: 1.5rem;
        }

        .skills-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
        }

        .skill-card {
            background: white;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: var(--shadow);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .skill-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: var(--gradient);
            transition: left 0.5s ease;
            z-index: 1;
        }

        .skill-card:hover::before {
            left: 0;
        }

        .skill-card:hover {
            transform: translateY(-10px);
            color: white;
        }

        .skill-card > * {
            position: relative;
            z-index: 2;
        }

        .skill-icon {
            font-size: 3rem;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }

        .skill-card:hover .skill-icon {
            -webkit-text-fill-color: white;
        }

        /* Articles Section */
        .articles-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2.5rem;
        }

        .article-card {
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            position: relative;
        }

        .article-card:hover {
            transform: translateY(-10px);
            box-shadow: var(--shadow-lg);
        }

        .article-image {
            width: 100%;
            height: 200px;
            background-size: cover;
            background-position: center;
            position: relative;
        }

        .article-category {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: var(--accent);
            color: white;
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .article-content {
            padding: 2rem;
        }

        .article-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--dark);
            line-height: 1.4;
        }

        .article-excerpt {
            color: #666;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }

        .article-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: #888;
        }

        .article-tags {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .tag {
            background: var(--light);
            color: var(--dark);
            padding: 0.2rem 0.8rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }

        /* Applications Section */
        .apps-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }

        .app-card {
            background: white;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: var(--shadow);
            text-align: center;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .app-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
        }

        .app-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }

        .app-title {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--dark);
        }

        .app-description {
            color: #666;
            margin-bottom: 1.5rem;
        }

        .app-features {
            list-style: none;
            margin-bottom: 2rem;
        }

        .app-features li {
            padding: 0.3rem 0;
            font-size: 0.9rem;
            color: var(--success);
        }

        .app-features li::before {
            content: '✓';
            margin-left: 0.5rem;
            font-weight: bold;
        }

        /* Tools Section */
        .tools-container {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: var(--shadow);
            margin-top: 3rem;
        }

        .tool {
            display: none;
            animation: fadeIn 0.5s ease;
        }

        .tool.active {
            display: block;
        }

        .tool-nav {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        .tool-btn {
            padding: 0.8rem 1.5rem;
            border: 2px solid var(--primary);
            background: transparent;
            color: var(--primary);
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .tool-btn.active,
        .tool-btn:hover {
            background: var(--primary);
            color: white;
        }

        .input-group {
            margin-bottom: 1.5rem;
        }

        .input-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: var(--dark);
        }

        .input-group input,
        .input-group select,
        .input-group textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 1rem;
            transition: all 0.3s ease;
            font-family: inherit;
        }

        .input-group input:focus,
        .input-group select:focus,
        .input-group textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .result-box {
            background: var(--light);
            padding: 1.5rem;
            border-radius: 10px;
            margin-top: 1rem;
            border: 2px dashed #ddd;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: monospace;
            font-size: 1.1rem;
        }

        /* Stats Section */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
        }

        .stat-card {
            background: var(--gradient);
            color: white;
            padding: 3rem 2rem;
            border-radius: 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: pulse 4s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.1; }
            50% { transform: scale(1.1); opacity: 0.2; }
        }

        .stat-number {
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 2;
        }

        .stat-label {
            font-size: 1.1rem;
            font-weight: 600;
            position: relative;
            z-index: 2;
        }

        /* Contact Section */
        .contact-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4rem;
            align-items: start;
        }

        .contact-info {
            background: var(--gradient);
            padding: 3rem;
            border-radius: 20px;
            color: white;
        }

        .contact-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .contact-icon {
            width: 50px;
            height: 50px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .contact-form {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: var(--shadow);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: var(--dark);
        }

        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 1rem;
            transition: all 0.3s ease;
            font-family: inherit;
        }

        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .message {
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            border-radius: 10px;
            font-weight: 600;
        }

        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        /* Newsletter */
        .newsletter {
            background: var(--gradient);
            color: white;
            padding: 4rem 0;
            text-align: center;
        }

        .newsletter-form {
            display: flex;
            gap: 1rem;
            justify-content: center;
            max-width: 500px;
            margin: 2rem auto 0;
        }

        .newsletter-form input {
            flex: 1;
            padding: 15px 20px;
            border: none;
            border-radius: 50px;
            font-size: 1rem;
        }

        .newsletter-form button {
            padding: 15px 30px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 50px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .newsletter-form button:hover {
            background: #ff5252;
            transform: translateY(-2px);
        }

        /* Footer */
        footer {
            background: var(--dark);
            color: white;
            padding: 4rem 0 2rem;
        }

        .footer-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 3rem;
            margin-bottom: 2rem;
        }

        .footer-section h3 {
            font-size: 1.3rem;
            margin-bottom: 1rem;
            color: var(--accent);
        }

        .footer-section p,
        .footer-section li {
            color: #ccc;
            line-height: 1.6;
        }

        .footer-section ul {
            list-style: none;
        }

        .footer-section ul li {
            padding: 0.3rem 0;
        }

        .footer-section ul li a {
            color: #ccc;
            text-decoration: none;
            transition: color 0.3s ease;
        }

        .footer-section ul li a:hover {
            color: var(--accent);
        }

        .social-links {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }

        .social-links a {
            width: 40px;
            height: 40px;
            background: var(--gradient);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            text-decoration: none;
            transition: transform 0.3s ease;
        }

        .social-links a:hover {
            transform: translateY(-3px);
        }

        .footer-bottom {
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid #444;
            color: #999;
        }

        /* Animations */
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        /* Scroll Animations */
        .animate-on-scroll {
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.6s ease;
        }

        .animate-on-scroll.animated {
            opacity: 1;
            transform: translateY(0);
        }

        /* Back to Top Button */
        .back-to-top {
            position: fixed;
            bottom: 30px;
            left: 30px;
            width: 50px;
            height: 50px;
            background: var(--gradient);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .back-to-top:hover {
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }

        .back-to-top.visible {
            display: flex;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .mobile-menu-btn {
                display: block;
            }

            .nav-links {
                position: fixed;
                top: 100%;
                left: 0;
                width: 100%;
                background: white;
                flex-direction: column;
                padding: 2rem;
                box-shadow: var(--shadow);
                transform: translateY(-100%);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }

            .nav-links.active {
                transform: translateY(0);
                opacity: 1;
                visibility: visible;
            }

            .hero {
                padding: 150px 0 80px;
            }

            .hero-cta {
                flex-direction: column;
                align-items: center;
            }

            .about-grid,
            .contact-grid {
                grid-template-columns: 1fr;
                gap: 2rem;
            }

            .section {
                padding: 60px 0;
            }

            .section-header {
                margin-bottom: 3rem;
            }

            .newsletter-form {
                flex-direction: column;
                gap: 1rem;
            }

            .tools-container {
                padding: 2rem;
            }

            .tool-nav {
                gap: 0.5rem;
            }

            .tool-btn {
                padding: 0.6rem 1rem;
                font-size: 0.9rem;
            }
        }

        @media (max-width: 480px) {
            .container {
                padding: 0 15px;
            }

            .hero h1 {
                font-size: 2rem;
            }

            .hero-subtitle {
                font-size: 1rem;
            }

            .section-title {
                font-size: 1.8rem;
            }

            .contact-form,
            .contact-info {
                padding: 2rem;
            }

            .back-to-top {
                bottom: 20px;
                left: 20px;
            }
        }

        /* Print Styles */
        @media print {
            .loading-screen,
            header,
            .back-to-top,
            .newsletter {
                display: none;
            }

            body {
                font-size: 12pt;
                line-height: 1.4;
            }

            .section {
                padding: 20px 0;
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <!-- Loading Screen -->
    <div class="loading-screen" id="loadingScreen">
        <div class="loading-content">
            <div class="spinner"></div>
            <h3>جاري التحميل...</h3>
        </div>
    </div>

    <!-- Header -->
    <header id="header">
        <nav class="container">
            <div class="logo">مهندس المواقع</div>
            <ul class="nav-links" id="navLinks">
                <li><a href="#home" class="nav-link">الرئيسية</a></li>
                <li><a href="#about" class="nav-link">نبذة عني</a></li>
                <li><a href="#articles" class="nav-link">المقالات</a></li>
                <li><a href="#applications" class="nav-link">التطبيقات</a></li>
                <li><a href="#tools" class="nav-link">الأدوات</a></li>
                <li><a href="#contact" class="nav-link">تواصل معي</a></li>
            </ul>
            <button class="mobile-menu-btn" id="mobileMenuBtn">
                <i class="fas fa-bars"></i>
            </button>
        </nav>
    </header>

    <!-- Hero Section -->
    <section id="home" class="hero">
        <div class="floating-shapes">
            <div class="shape"></div>
            <div class="shape"></div>
            <div class="shape"></div>
        </div>
        <div class="container">
            <div class="hero-content">
                <h1>مهندس مواقع إلكترونية محترف</h1>
                <p class="hero-subtitle">أحول أفكارك إلى مواقع ويب عصرية وتفاعلية باستخدام أحدث التقنيات</p>
                <div class="hero-cta">
                    <a href="#contact" class="btn btn-primary">
                        <i class="fas fa-rocket"></i>
                        ابدأ مشروعك
                    </a>
                    <a href="#about" class="btn btn-secondary">
                        <i class="fas fa-user"></i>
                        تعرف علي أكثر
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- About Section -->
    <section id="about" class="section">
        <div class="container">
            <div class="section-header animate-on-scroll">
                <h2 class="section-title">نبذة عني</h2>
                <p class="section-subtitle">مهندس مواقع شغوف بالتطوير والإبداع في عالم الويب</p>
            </div>

            <div class="about-grid animate-on-scroll">
                <div class="about-text">
                    <p>مرحباً، أنا مهندس مواقع إلكترونية معتمد مع خبرة <?php echo $stats['experience']; ?> سنوات في مجال تطوير الويب. حاصل على شهادة جامعية في هندسة البرمجيات ومتخصص في إنشاء مواقع ويب حديثة وتفاعلية.</p>
                    
                    <p>أؤمن بأن التصميم الجيد يجب أن يجمع بين الجمال والوظائف العملية. أعمل مع العملاء لتحويل أفكارهم إلى مواقع ويب احترافية تحقق أهدافهم التجارية وتوفر تجربة مستخدم استثنائية.</p>
                    
                    <p>أتقن العديد من لغات البرمجة والتقنيات الحديثة، وأحرص دائماً على متابعة آخر التطورات في عالم تطوير الويب والذكاء الاصطناعي.</p>

                    <div class="hero-cta" style="justify-content: flex-start; margin-top: 2rem;">
                        <a href="#contact" class="btn btn-primary">
                            <i class="fas fa-download"></i>
                            تحميل السيرة الذاتية
                        </a>
                    </div>
                </div>

                <div class="skills-grid">
                    <div class="skill-card">
                        <div class="skill-icon">
                            <i class="fab fa-html5"></i>
                        </div>
                        <h3>تطوير الواجهات الأمامية</h3>
                        <p>HTML5, CSS3, JavaScript, React, Vue.js</p>
                    </div>
                    <div class="skill-card">
                        <div class="skill-icon">
                            <i class="fas fa-server"></i>
                        </div>
                        <h3>تطوير الخلفية</h3>
                        <p>PHP, Python, Node.js, MySQL, MongoDB</p>
                    </div>
                    <div class="skill-card">
                        <div class="skill-icon">
                            <i class="fab fa-wordpress"></i>
                        </div>
                        <h3>إدارة المحتوى</h3>
                        <p>WordPress, Laravel, Django</p>
                    </div>
                    <div class="skill-card">
                        <div class="skill-icon">
                            <i class="fas fa-mobile-alt"></i>
                        </div>
                        <h3>التصميم التفاعلي</h3>
                        <p>Bootstrap, Tailwind, Responsive Design</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="section">
        <div class="container">
            <div class="stats-grid animate-on-scroll">
                <div class="stat-card">
                    <div class="stat-number"><?php echo $stats['projects']; ?>+</div>
                    <div class="stat-label">مشروع مكتمل</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number"><?php echo $stats['clients']; ?>+</div>
                    <div class="stat-label">عميل راضٍ</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number"><?php echo $stats['experience']; ?>+</div>
                    <div class="stat-label">سنوات خبرة</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number"><?php echo $stats['articles']; ?>+</div>
                    <div class="stat-label">مقال تقني</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Articles Section -->
    <section id="articles" class="section">
        <div class="container">
            <div class="section-header animate-on-scroll">
                <h2 class="section-title">المقالات التقنية</h2>
                <p class="section-subtitle">مشاركة المعرفة والخبرات في عالم تطوير الويب</p>
            </div>

            <div class="articles-grid animate-on-scroll">
                <?php foreach ($articles as $article): ?>
                <article class="article-card">
                    <div class="article-image" style="background-image: url('<?php echo $article['image']; ?>')">
                        <span class="article-category"><?php echo $article['category']; ?></span>
                    </div>
                    <div class="article-content">
                        <div class="article-meta">
                            <span><i class="fas fa-calendar"></i> <?php echo date('d M Y', strtotime($article['date'])); ?></span>
                            <span><i class="fas fa-clock"></i> 5 دقائق قراءة</span>
                        </div>
                        <h3 class="article-title"><?php echo $article['title']; ?></h3>
                        <p class="article-excerpt"><?php echo $article['excerpt']; ?></p>
                        <div class="article-tags">
                            <?php foreach ($article['tags'] as $tag): ?>
                            <span class="tag"><?php echo $tag; ?></span>
                            <?php endforeach; ?>
                        </div>
                        <a href="#" class="btn btn-primary">
                            <i class="fas fa-arrow-left"></i>
                            اقرأ المزيد
                        </a>
                    </div>
                </article>
                <?php endforeach; ?>
            </div>
        </div>
    </section>

    <!-- Applications Section -->
    <section id="applications" class="section">
        <div class="container">
            <div class="section-header animate-on-scroll">
                <h2 class="section-title">التطبيقات والأدوات</h2>
                <p class="section-subtitle">مجموعة من الأدوات المفيدة للمطورين والمصممين</p>
            </div>

            <div class="apps-grid animate-on-scroll">
                <?php foreach ($applications as $app): ?>
                <div class="app-card">
                    <div class="app-icon"><?php echo $app['icon']; ?></div>
                    <h3 class="app-title"><?php echo $app['name']; ?></h3>
                    <p class="app-description"><?php echo $app['description']; ?></p>
                    <ul class="app-features">
                        <?php foreach ($app['features'] as $feature): ?>
                        <li><?php echo $feature; ?></li>
                        <?php endforeach; ?>
                    </ul>
                    <a href="<?php echo $app['demo_url']; ?>" class="btn btn-primary">
                        <i class="fas fa-play"></i>
                        جرب الأداة
                    </a>
                </div>
                <?php endforeach; ?>
            </div>
        </div>
    </section>

    <!-- Tools Section -->
    <section id="tools" class="section">
        <div class="container">
            <div class="section-header animate-on-scroll">
                <h2 class="section-title">الأدوات التفاعلية</h2>
                <p class="section-subtitle">استخدم هذه الأدوات المجانية لتسهيل عملك</p>
            </div>

            <div class="tools-container animate-on-scroll">
                <div class="tool-nav">
                    <button class="tool-btn active" onclick="showTool('password-generator')">منشئ كلمات المرور</button>
                    <button class="tool-btn" onclick="showTool('color-converter')">محول الألوان</button>
                    <button class="tool-btn" onclick="showTool('qr-generator')">مولد QR Code</button>
                    <button class="tool-btn" onclick="showTool('calculator')">الحاسبة المتقدمة</button>
                </div>

                <!-- Password Generator -->
                <div id="password-generator" class="tool active">
                    <h3>منشئ كلمات المرور الآمنة</h3>
                    <div class="input-group">
                        <label>طول كلمة المرور</label>
                        <input type="range" id="passwordLength" min="8" max="50" value="16" oninput="updatePasswordLength()">
                        <span id="lengthValue">16</span>
                    </div>
                    <div class="input-group">
                        <label><input type="checkbox" id="includeNumbers" checked> تضمين الأرقام</label>
                    </div>
                    <div class="input-group">
                        <label><input type="checkbox" id="includeSymbols" checked> تضمين الرموز الخاصة</label>
                    </div>
                    <button class="btn btn-primary" onclick="generatePassword()">إنشاء كلمة مرور</button>
                    <div class="result-box" id="passwordResult">اضغط لإنشاء كلمة مرور</div>
                    <button class="btn btn-secondary" onclick="copyPassword()" style="margin-top: 1rem;">نسخ كلمة المرور</button>
                </div>

                <!-- Color Converter -->
                <div id="color-converter" class="tool">
                    <h3>محول الألوان</h3>
                    <div class="input-group">
                        <label>اللون (HEX)</label>
                        <input type="text" id="hexColor" placeholder="#FF5733" oninput="convertColor()">
                    </div>
                    <div class="result-box" id="colorResult">
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div id="colorPreview" style="width: 50px; height: 50px; border-radius: 10px; background: #ccc;"></div>
                            <div id="colorValues">أدخل كود HEX للتحويل</div>
                        </div>
                    </div>
                </div>

                <!-- QR Generator -->
                <div id="qr-generator" class="tool">
                    <h3>مولد رموز QR</h3>
                    <div class="input-group">
                        <label>النص أو الرابط</label>
                        <textarea id="qrText" placeholder="أدخل النص أو الرابط هنا..." rows="3"></textarea>
                    </div>
                    <button class="btn btn-primary" onclick="generateQR()">إنشاء رمز QR</button>
                    <div class="result-box" id="qrResult">سيظهر رمز QR هنا</div>
                </div>

                <!-- Calculator -->
                <div id="calculator" class="tool">
                    <h3>الحاسبة المتقدمة</h3>
                    <div class="input-group">
                        <label>العملية الحسابية</label>
                        <input type="text" id="calcInput" placeholder="مثال: 2 + 3 * 4" oninput="calculate()">
                    </div>
                    <div class="result-box" id="calcResult">أدخل عملية حسابية</div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin-top: 1rem;">
                        <button class="btn btn-secondary" onclick="addToCalc('7')">7</button>
                        <button class="btn btn-secondary" onclick="addToCalc('8')">8</button>
                        <button class="btn btn-secondary" onclick="addToCalc('9')">9</button>
                        <button class="btn btn-secondary" onclick="addToCalc('/')">/</button>
                        <button class="btn btn-secondary" onclick="addToCalc('4')">4</button>
                        <button class="btn btn-secondary" onclick="addToCalc('5')">5</button>
                        <button class="btn btn-secondary" onclick="addToCalc('6')">6</button>
                        <button class="btn btn-secondary" onclick="addToCalc('*')">×</button>
                        <button class="btn btn-secondary" onclick="addToCalc('1')">1</button>
                        <button class="btn btn-secondary" onclick="addToCalc('2')">2</button>
                        <button class="btn btn-secondary" onclick="addToCalc('3')">3</button>
                        <button class="btn btn-secondary" onclick="addToCalc('-')">-</button>
                        <button class="btn btn-secondary" onclick="addToCalc('0')">0</button>
                        <button class="btn btn-secondary" onclick="addToCalc('.')">.</button>
                        <button class="btn btn-secondary" onclick="clearCalc()">C</button>
                        <button class="btn btn-secondary" onclick="addToCalc('+')">+</button>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="section">
        <div class="container">
            <div class="section-header animate-on-scroll">
                <h2 class="section-title">تواصل معي</h2>
                <p class="section-subtitle">لنبدأ رحلة إنشاء موقعك الإلكتروني المميز</p>
            </div>

            <div class="contact-grid animate-on-scroll">
                <div class="contact-info">
                    <h3>معلومات التواصل</h3>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-envelope"></i>
                        </div>
                        <div>
                            <h4>البريد الإلكتروني</h4>
                            <p>info@webdeveloper.com</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-phone"></i>
                        </div>
                        <div>
                            <h4>رقم الهاتف</h4>
                            <p>+90 555 123 4567</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-map-marker-alt"></i>
                        </div>
                        <div>
                            <h4>الموقع</h4>
                            <p>قيصري، تركيا</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div>
                            <h4>ساعات العمل</h4>
                            <p>الأحد - الخميس: 9:00 - 18:00</p>
                        </div>
                    </div>
                </div>

                <form class="contact-form" method="POST">
                    <input type="hidden" name="contact_form" value="1">
                    
                    <?php if (isset($messages['contact'])): ?>
                        <div class="message success"><?php echo $messages['contact']; ?></div>
                    <?php endif; ?>

                    <div class="form-group">
                        <label for="name">الاسم الكامل</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">البريد الإلكتروني</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="subject">الموضوع</label>
                        <input type="text" id="subject" name="subject" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="message">الرسالة</label>
                        <textarea id="message" name="message" rows="5" required></textarea>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-paper-plane"></i>
                        إرسال الرسالة
                    </button>
                </form>
            </div>
        </div>
    </section>

    <!-- Newsletter Section -->
    <section class="newsletter">
        <div class="container">
            <h2>اشترك في النشرة البريدية</h2>
            <p>احصل على آخر الأخبار والمقالات التقنية</p>
            
            <?php if ($newsletter_message): ?>
                <div class="message success" style="background: rgba(255,255,255,0.2); color: white; border-color: rgba(255,255,255,0.3);">
                    <?php echo $newsletter_message; ?>
                </div>
            <?php endif; ?>
            
            <form class="newsletter-form" method="POST">
                <input type="hidden" name="newsletter_form" value="1">
                <input type="email" name="newsletter_email" placeholder="أدخل بريدك الإلكتروني" required>
                <button type="submit">اشتراك</button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="container">
            <div class="footer-content">
                <div class="footer-section">
                    <h3>مهندس المواقع</h3>
                    <p>متخصص في تطوير المواقع الإلكترونية الحديثة والتفاعلية. أحول أفكارك إلى واقع رقمي مبهر.</p>
                    <div class="social-links">
                        <a href="#"><i class="fab fa-facebook"></i></a>
                        <a href="#"><i class="fab fa-twitter"></i></a>
                        <a href="#"><i class="fab fa-linkedin"></i></a>
                        <a href="#"><i class="fab fa-github"></i></a>
                        <a href="#"><i class="fab fa-instagram"></i></a>
                    </div>
                </div>
                <div class="footer-section">
                    <h3>الخدمات</h3>
                    <ul>
                        <li><a href="#">تصميم المواقع</a></li>
                        <li><a href="#">تطوير التطبيقات</a></li>
                        <li><a href="#">تحسين محركات البحث</a></li>
                        <li><a href="#">الاستشارات التقنية</a></li>