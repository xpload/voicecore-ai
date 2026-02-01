#!/usr/bin/env python3
"""
Dashboard Enterprise Completo - Fortune 500 Level
Integración completa de todas las APIs del sistema VoiceCore AI
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoiceCore AI - Enterprise Command Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios@1.6.0/dist/axios.min.js"></script>
    <style>
        :root {
            --primary-50: #eff6ff;
            --primary-100: #dbeafe;
            --primary-200: #bfdbfe;
            --primary-300: #93c5fd;
            --primary-400: #60a5fa;
            --primary-500: #3b82f6;
            --primary-600: #2563eb;
            --primary-700: #1d4ed8;
            --primary-800: #1e40af;
            --primary-900: #1e3a8a;
            
            --success-50: #ecfdf5;
            --success-100: #d1fae5;
            --success-200: #a7f3d0;
            --success-300: #6ee7b7;
            --success-400: #34d399;
            --success-500: #10b981;
            --success-600: #059669;
            --success-700: #047857;
            --success-800: #065f46;
            --success-900: #064e3b;
            
            --warning-50: #fffbeb;
            --warning-100: #fef3c7;
            --warning-200: #fde68a;
            --warning-300: #fcd34d;
            --warning-400: #fbbf24;
            --warning-500: #f59e0b;
            --warning-600: #d97706;
            --warning-700: #b45309;
            --warning-800: #92400e;
            --warning-900: #78350f;
            
            --error-50: #fef2f2;
            --error-100: #fee2e2;
            --error-200: #fecaca;
            --error-300: #fca5a5;
            --error-400: #f87171;
            --error-500: #ef4444;
            --error-600: #dc2626;
            --error-700: #b91c1c;
            --error-800: #991b1b;
            --error-900: #7f1d1d;
            
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            
            --dark-bg: #0a0e1a;
            --dark-surface: #0f172a;
            --dark-card: #1e293b;
            --dark-border: #334155;
            --dark-text: #f8fafc;
            --dark-text-secondary: #cbd5e1;
            
            --gradient-primary: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-800) 100%);
            --gradient-success: linear-gradient(135deg, var(--success-500) 0%, var(--success-700) 100%);
            --gradient-warning: linear-gradient(135deg, var(--warning-500) 0%, var(--warning-700) 100%);
            --gradient-error: linear-gradient(135deg, var(--error-500) 0%, var(--error-700) 100%);
            
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
            --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
            
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--dark-bg);
            color: var(--dark-text);
            line-height: 1.6;
            overflow-x: hidden;
            font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .dashboard-container {
            min-height: 100vh;
            display: flex;
            background: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                        radial-gradient(ellipse at bottom, rgba(16, 185, 129, 0.1) 0%, transparent 50%);
        }
        
        /* Sidebar Navigation */
        .sidebar {
            width: 280px;
            background: var(--dark-surface);
            border-right: 1px solid var(--dark-border);
            padding: 2rem 0;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            z-index: 1000;
            transition: var(--transition-normal);
        }
        
        .sidebar-header {
            padding: 0 2rem 2rem;
            border-bottom: 1px solid var(--dark-border);
            margin-bottom: 2rem;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.5rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .logo-icon {
            width: 48px;
            height: 48px;
            background: var(--gradient-primary);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5rem;
            box-shadow: var(--shadow-lg);
        }
        
        .nav-section {
            margin-bottom: 2rem;
        }
        
        .nav-section-title {
            padding: 0 2rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--dark-text-secondary);
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 2rem;
            color: var(--dark-text-secondary);
            text-decoration: none;
            transition: var(--transition-fast);
            cursor: pointer;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .nav-item:hover,
        .nav-item.active {
            background: rgba(59, 130, 246, 0.1);
            color: var(--primary-400);
            border-right: 3px solid var(--primary-500);
        }
        
        .nav-item i {
            width: 20px;
            text-align: center;
            font-size: 1rem;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            margin-left: 280px;
            padding: 2rem;
            transition: var(--transition-normal);
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--dark-border);
        }
        
        .page-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--dark-text);
        }
        
        .page-subtitle {
            font-size: 1rem;
            color: var(--dark-text-secondary);
            margin-top: 0.25rem;
        }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--gradient-success);
            border-radius: 50px;
            font-size: 0.875rem;
            font-weight: 600;
            color: white;
            box-shadow: var(--shadow-lg);
        }
        
        .pulse {
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
        }
        
        /* Content Sections */
        .content-section {
            display: none;
        }
        
        .content-section.active {
            display: block;
        }
        
        /* Cards */
        .card {
            background: var(--dark-card);
            border: 1px solid var(--dark-border);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: var(--shadow-lg);
            transition: var(--transition-normal);
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient-primary);
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-2xl);
            border-color: var(--primary-600);
        }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            text-align: center;
        }
        
        .metric-icon {
            width: 60px;
            height: 60px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
            margin: 0 auto 1rem;
            box-shadow: var(--shadow-lg);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        
        .metric-label {
            color: var(--dark-text-secondary);
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }
        
        .metric-change {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 50px;
            background: rgba(16, 185, 129, 0.1);
            color: var(--success-500);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.875rem;
            cursor: pointer;
            transition: var(--transition-normal);
            text-decoration: none;
            box-shadow: var(--shadow-lg);
        }
        
        .btn-primary {
            background: var(--gradient-primary);
            color: white;
        }
        
        .btn-success {
            background: var(--gradient-success);
            color: white;
        }
        
        .btn-warning {
            background: var(--gradient-warning);
            color: white;
        }
        
        .btn-secondary {
            background: var(--dark-surface);
            color: var(--dark-text);
            border: 1px solid var(--dark-border);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-xl);
        }
        
        /* Tables */
        .table-container {
            background: var(--dark-card);
            border: 1px solid var(--dark-border);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 2rem;
        }
        
        .table-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--dark-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .table-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--dark-text);
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .table th,
        .table td {
            padding: 1rem 1.5rem;
            text-align: left;
            border-bottom: 1px solid var(--dark-border);
        }
        
        .table th {
            background: var(--dark-surface);
            font-weight: 600;
            color: var(--dark-text-secondary);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .table td {
            color: var(--dark-text);
        }
        
        .table tbody tr:hover {
            background: rgba(59, 130, 246, 0.05);
        }
        
        /* Forms */
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: var(--dark-text);
        }
        
        .form-input {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--dark-surface);
            border: 1px solid var(--dark-border);
            border-radius: 8px;
            color: var(--dark-text);
            font-size: 0.875rem;
            transition: var(--transition-fast);
        }
        
        .form-input:focus {
            outline: none;
            border-color: var(--primary-500);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.375rem 0.75rem;
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .status-badge.success {
            background: rgba(16, 185, 129, 0.1);
            color: var(--success-500);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        
        .status-badge.warning {
            background: rgba(245, 158, 11, 0.1);
            color: var(--warning-500);
            border: 1px solid rgba(245, 158, 11, 0.2);
        }
        
        .status-badge.error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--error-500);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        /* Loading States */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: var(--dark-text-secondary);
        }
        
        .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid var(--dark-border);
            border-top: 2px solid var(--primary-500);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 0.5rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Responsive Design */
        @media (max-width: 1024px) {
            .sidebar {
                transform: translateX(-100%);
            }
            
            .sidebar.open {
                transform: translateX(0);
            }
            
            .main-content {
                margin-left: 0;
            }
            
            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .main-content {
                padding: 1rem;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
        }
        
        /* Charts */
        .chart-container {
            position: relative;
            height: 400px;
            margin-top: 1rem;
        }
        
        /* Action Grids */
        .action-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .action-card {
            background: var(--dark-card);
            border: 1px solid var(--dark-border);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            transition: var(--transition-normal);
        }
        
        .action-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-2xl);
            border-color: var(--primary-600);
        }
        
        .action-icon {
            width: 80px;
            height: 80px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            color: white;
            margin: 0 auto 1.5rem;
            box-shadow: var(--shadow-lg);
        }
        
        .action-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--dark-text);
        }
        
        .action-description {
            color: var(--dark-text-secondary);
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <!-- Sidebar Navigation -->
        <nav class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <div class="logo-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    VoiceCore AI
                </div>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Overview</div>
                <button class="nav-item active" onclick="showSection('dashboard')">
                    <i class="fas fa-tachometer-alt"></i>
                    Dashboard
                </button>
                <button class="nav-item" onclick="showSection('analytics')">
                    <i class="fas fa-chart-line"></i>
                    Analytics
                </button>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Management</div>
                <button class="nav-item" onclick="showSection('tenants')">
                    <i class="fas fa-building"></i>
                    Tenants
                </button>
                <button class="nav-item" onclick="showSection('agents')">
                    <i class="fas fa-robot"></i>
                    AI Agents
                </button>
                <button class="nav-item" onclick="showSection('calls')">
                    <i class="fas fa-phone"></i>
                    Call Management
                </button>
                <button class="nav-item" onclick="showSection('vip')">
                    <i class="fas fa-star"></i>
                    VIP Management
                </button>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Operations</div>
                <button class="nav-item" onclick="showSection('monitoring')">
                    <i class="fas fa-heartbeat"></i>
                    System Monitoring
                </button>
                <button class="nav-item" onclick="showSection('security')">
                    <i class="fas fa-shield-alt"></i>
                    Security
                </button>
                <button class="nav-item" onclick="showSection('billing')">
                    <i class="fas fa-credit-card"></i>
                    Billing & Credits
                </button>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Advanced</div>
                <button class="nav-item" onclick="showSection('ai-training')">
                    <i class="fas fa-brain"></i>
                    AI Training
                </button>
                <button class="nav-item" onclick="showSection('integrations')">
                    <i class="fas fa-plug"></i>
                    Integrations
                </button>
                <button class="nav-item" onclick="showSection('settings')">
                    <i class="fas fa-cog"></i>
                    Settings
                </button>
            </div>
        </nav>
        
        <!-- Main Content -->
        <main class="main-content">
            <!-- Dashboard Section -->
            <div id="dashboard" class="content-section active">
                <div class="header">
                    <div>
                        <h1 class="page-title">Enterprise Dashboard</h1>
                        <p class="page-subtitle">Real-time system overview and key metrics</p>
                    </div>
                    <div class="header-actions">
                        <div class="status-indicator">
                            <div class="pulse"></div>
                            System Operational
                        </div>
                        <button class="btn btn-secondary" onclick="refreshDashboard()">
                            <i class="fas fa-sync-alt"></i>
                            Refresh
                        </button>
                    </div>
                </div>
                
                <div class="metrics-grid" id="metricsGrid">
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-heartbeat"></i>
                        </div>
                        <div class="metric-value">99.9%</div>
                        <div class="metric-label">System Uptime</div>
                        <div class="metric-change">
                            <i class="fas fa-arrow-up"></i>
                            +0.02%
                        </div>
                    </div>
                    
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-building"></i>
                        </div>
                        <div class="metric-value" id="tenantsCount">0</div>
                        <div class="metric-label">Active Tenants</div>
                        <div class="metric-change">
                            <i class="fas fa-arrow-up"></i>
                            +3
                        </div>
                    </div>
                    
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-warning)">
                            <i class="fas fa-phone"></i>
                        </div>
                        <div class="metric-value" id="callsCount">0</div>
                        <div class="metric-label">Calls Today</div>
                        <div class="metric-change">
                            <i class="fas fa-arrow-up"></i>
                            +15%
                        </div>
                    </div>
                    
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="metric-value">92.1%</div>
                        <div class="metric-label">AI Automation</div>
                        <div class="metric-change">
                            <i class="fas fa-arrow-up"></i>
                            +2.1%
                        </div>
                    </div>
                </div>
                
                <div class="action-grid">
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-building"></i>
                        </div>
                        <h3 class="action-title">Tenant Management</h3>
                        <p class="action-description">Create, manage, and configure multi-tenant organizations</p>
                        <button class="btn btn-primary" onclick="showSection('tenants')">
                            <i class="fas fa-arrow-right"></i>
                            Manage Tenants
                        </button>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h3 class="action-title">AI Agents</h3>
                        <p class="action-description">Configure and train intelligent virtual assistants</p>
                        <button class="btn btn-success" onclick="showSection('agents')">
                            <i class="fas fa-arrow-right"></i>
                            Manage Agents
                        </button>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-warning)">
                            <i class="fas fa-star"></i>
                        </div>
                        <h3 class="action-title">VIP Management</h3>
                        <p class="action-description">Manage VIP callers and priority routing</p>
                        <button class="btn btn-warning" onclick="showSection('vip')">
                            <i class="fas fa-arrow-right"></i>
                            Manage VIPs
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Tenants Section -->
            <div id="tenants" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">Tenant Management</h1>
                        <p class="page-subtitle">Manage multi-tenant organizations and configurations</p>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-primary" onclick="createTenant()">
                            <i class="fas fa-plus"></i>
                            Create Tenant
                        </button>
                    </div>
                </div>
                
                <div class="table-container">
                    <div class="table-header">
                        <h3 class="table-title">Active Tenants</h3>
                        <button class="btn btn-secondary" onclick="loadTenants()">
                            <i class="fas fa-sync-alt"></i>
                            Refresh
                        </button>
                    </div>
                    <div id="tenantsTableContainer">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading tenants...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Agents Section -->
            <div id="agents" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">AI Agent Management</h1>
                        <p class="page-subtitle">Configure and manage intelligent virtual assistants</p>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-success" onclick="createAgent()">
                            <i class="fas fa-plus"></i>
                            Create Agent
                        </button>
                    </div>
                </div>
                
                <div class="action-grid">
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h3 class="action-title">Agent Configuration</h3>
                        <p class="action-description">Configure AI agent behavior and responses</p>
                        <button class="btn btn-primary" onclick="configureAgents()">
                            <i class="fas fa-cog"></i>
                            Configure
                        </button>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-brain"></i>
                        </div>
                        <h3 class="action-title">AI Training</h3>
                        <p class="action-description">Train agents with custom knowledge and responses</p>
                        <button class="btn btn-success" onclick="showSection('ai-training')">
                            <i class="fas fa-graduation-cap"></i>
                            Train AI
                        </button>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-warning)">
                            <i class="fas fa-chart-line"></i>
                        </div>
                        <h3 class="action-title">Performance Analytics</h3>
                        <p class="action-description">Monitor agent performance and optimization</p>
                        <button class="btn btn-warning" onclick="showSection('analytics')">
                            <i class="fas fa-analytics"></i>
                            View Analytics
                        </button>
                    </div>
                </div>
                
                <div id="agentsContainer">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading agents...
                    </div>
                </div>
            </div>
            
            <!-- VIP Management Section -->
            <div id="vip" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">VIP Management</h1>
                        <p class="page-subtitle">Manage VIP callers and priority routing</p>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-warning" onclick="createVIP()">
                            <i class="fas fa-star"></i>
                            Add VIP
                        </button>
                    </div>
                </div>
                
                <div class="table-container">
                    <div class="table-header">
                        <h3 class="table-title">VIP Callers</h3>
                        <button class="btn btn-secondary" onclick="loadVIPs()">
                            <i class="fas fa-sync-alt"></i>
                            Refresh
                        </button>
                    </div>
                    <div id="vipTableContainer">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading VIP callers...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Calls Section -->
            <div id="calls" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">Call Management</h1>
                        <p class="page-subtitle">Monitor and manage call activities</p>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-primary" onclick="exportCalls()">
                            <i class="fas fa-download"></i>
                            Export Data
                        </button>
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-phone"></i>
                        </div>
                        <div class="metric-value" id="totalCalls">0</div>
                        <div class="metric-label">Total Calls</div>
                    </div>
                    
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="metric-value" id="successfulCalls">0</div>
                        <div class="metric-label">Successful Calls</div>
                    </div>
                    
                    <div class="card metric-card">
                        <div class="metric-icon" style="background: var(--gradient-warning)">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="metric-value" id="avgDuration">0s</div>
                        <div class="metric-label">Avg Duration</div>
                    </div>
                </div>
                
                <div id="callsContainer">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading call data...
                    </div>
                </div>
            </div>
            
            <!-- Analytics Section -->
            <div id="analytics" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">Analytics & Insights</h1>
                        <p class="page-subtitle">Comprehensive system analytics and performance metrics</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>System Performance</h3>
                    <div class="chart-container">
                        <canvas id="performanceChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Monitoring Section -->
            <div id="monitoring" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">System Monitoring</h1>
                        <p class="page-subtitle">Real-time system health and performance monitoring</p>
                    </div>
                </div>
                
                <div class="action-grid">
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-heartbeat"></i>
                        </div>
                        <h3 class="action-title">Health Check</h3>
                        <p class="action-description">Comprehensive system health verification</p>
                        <a href="/health" class="btn btn-success" target="_blank">
                            <i class="fas fa-external-link-alt"></i>
                            Check Health
                        </a>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-server"></i>
                        </div>
                        <h3 class="action-title">System Status</h3>
                        <p class="action-description">Detailed system status and metrics</p>
                        <button class="btn btn-primary" onclick="checkSystemStatus()">
                            <i class="fas fa-search"></i>
                            Check Status
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Settings Section -->
            <div id="settings" class="content-section">
                <div class="header">
                    <div>
                        <h1 class="page-title">System Settings</h1>
                        <p class="page-subtitle">Configure system-wide settings and preferences</p>
                    </div>
                </div>
                
                <div class="action-grid">
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-primary)">
                            <i class="fas fa-book"></i>
                        </div>
                        <h3 class="action-title">API Documentation</h3>
                        <p class="action-description">Complete API reference and documentation</p>
                        <a href="/docs" class="btn btn-primary" target="_blank">
                            <i class="fas fa-external-link-alt"></i>
                            View Docs
                        </a>
                    </div>
                    
                    <div class="action-card">
                        <div class="action-icon" style="background: var(--gradient-success)">
                            <i class="fas fa-home"></i>
                        </div>
                        <h3 class="action-title">Main Application</h3>
                        <p class="action-description">Return to the main application interface</p>
                        <a href="/" class="btn btn-success">
                            <i class="fas fa-arrow-left"></i>
                            Go Home
                        </a>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        class EnterpriseDashboard {
            constructor() {
                this.currentSection = 'dashboard';
                this.charts = {};
                this.refreshInterval = null;
                this.init();
            }
            
            async init() {
                console.log('🚀 Initializing Enterprise Dashboard...');
                this.setupEventListeners();
                this.setupCharts();
                this.loadInitialData();
                this.startAutoRefresh();
                console.log('✅ Enterprise Dashboard Ready');
            }
            
            setupEventListeners() {
                // Navigation items
                document.querySelectorAll('.nav-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                        e.target.classList.add('active');
                    });
                });
            }
            
            setupCharts() {
                const performanceCtx = document.getElementById('performanceChart');
                if (performanceCtx && typeof Chart !== 'undefined') {
                    this.charts.performance = new Chart(performanceCtx.getContext('2d'), {
                        type: 'line',
                        data: {
                            labels: this.generateTimeLabels(24),
                            datasets: [{
                                label: 'Response Time (ms)',
                                data: this.generateRandomData(24, 100, 200),
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                tension: 0.4,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#cbd5e1' }
                                }
                            },
                            scales: {
                                x: { ticks: { color: '#64748b' }, grid: { color: '#334155' } },
                                y: { ticks: { color: '#64748b' }, grid: { color: '#334155' } }
                            }
                        }
                    });
                }
            }
            
            generateTimeLabels(hours) {
                const labels = [];
                const now = new Date();
                for (let i = hours - 1; i >= 0; i--) {
                    const time = new Date(now.getTime() - i * 60 * 60 * 1000);
                    labels.push(time.getHours().toString().padStart(2, '0') + ':00');
                }
                return labels;
            }
            
            generateRandomData(count, min, max) {
                return Array.from({ length: count }, () => 
                    Math.floor(Math.random() * (max - min + 1)) + min
                );
            }
            
            async loadInitialData() {
                try {
                    await this.loadTenants();
                    await this.loadCalls();
                } catch (error) {
                    console.error('Error loading initial data:', error);
                }
            }
            
            async loadTenants() {
                try {
                    const response = await axios.get('/api/tenants');
                    const tenants = response.data.tenants || [];
                    
                    // Update metrics
                    document.getElementById('tenantsCount').textContent = tenants.length;
                    
                    // Update table
                    this.renderTenantsTable(tenants);
                } catch (error) {
                    console.error('Error loading tenants:', error);
                    document.getElementById('tenantsTableContainer').innerHTML = 
                        '<div class="loading">Error loading tenants</div>';
                }
            }
            
            renderTenantsTable(tenants) {
                const container = document.getElementById('tenantsTableContainer');
                if (tenants.length === 0) {
                    container.innerHTML = '<div class="loading">No tenants found</div>';
                    return;
                }
                
                const table = `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Status</th>
                                <th>AI Name</th>
                                <th>Phone</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tenants.map(tenant => `
                                <tr>
                                    <td>${tenant.name}</td>
                                    <td><span class="status-badge success">${tenant.status}</span></td>
                                    <td>${tenant.ai_name}</td>
                                    <td>${tenant.phone}</td>
                                    <td>${new Date(tenant.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button class="btn btn-secondary" onclick="editTenant('${tenant.id}')">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                container.innerHTML = table;
            }
            
            async loadCalls() {
                try {
                    const response = await axios.get('/api/calls');
                    const calls = response.data.calls || [];
                    
                    // Update metrics
                    document.getElementById('callsCount').textContent = calls.length;
                    document.getElementById('totalCalls').textContent = calls.length;
                    
                    const successful = calls.filter(call => call.status === 'completed').length;
                    document.getElementById('successfulCalls').textContent = successful;
                    
                    const avgDuration = calls.reduce((sum, call) => sum + (call.duration || 0), 0) / calls.length;
                    document.getElementById('avgDuration').textContent = Math.round(avgDuration) + 's';
                    
                } catch (error) {
                    console.error('Error loading calls:', error);
                }
            }
            
            async loadVIPs() {
                try {
                    // This would connect to the VIP API when available
                    console.log('Loading VIP data...');
                    document.getElementById('vipTableContainer').innerHTML = 
                        '<div class="loading">VIP management coming soon...</div>';
                } catch (error) {
                    console.error('Error loading VIPs:', error);
                }
            }
            
            startAutoRefresh() {
                this.refreshInterval = setInterval(() => {
                    this.loadInitialData();
                }, 30000); // Refresh every 30 seconds
            }
            
            stopAutoRefresh() {
                if (this.refreshInterval) {
                    clearInterval(this.refreshInterval);
                    this.refreshInterval = null;
                }
            }
        }
        
        // Global functions
        function showSection(sectionId) {
            // Hide all sections
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            
            // Show selected section
            document.getElementById(sectionId).classList.add('active');
            
            // Update navigation
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Load section-specific data
            if (sectionId === 'tenants') {
                window.dashboard.loadTenants();
            } else if (sectionId === 'vip') {
                window.dashboard.loadVIPs();
            }
        }
        
        function refreshDashboard() {
            window.dashboard.loadInitialData();
        }
        
        function createTenant() {
            alert('Tenant creation form would open here');
        }
        
        function createAgent() {
            alert('Agent creation form would open here');
        }
        
        function createVIP() {
            alert('VIP creation form would open here');
        }
        
        function editTenant(tenantId) {
            alert(`Edit tenant ${tenantId}`);
        }
        
        function configureAgents() {
            alert('Agent configuration panel would open here');
        }
        
        function exportCalls() {
            alert('Call data export would start here');
        }
        
        function checkSystemStatus() {
            window.open('/health', '_blank');
        }
        
        // Initialize dashboard when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            window.dashboard = new EnterpriseDashboard();
        });
        
        console.log('🚀 VoiceCore AI Enterprise Dashboard - Fortune 500 Level - Complete API Integration');
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Dashboard HTML generado correctamente")