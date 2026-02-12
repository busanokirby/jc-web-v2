#!/usr/bin/env python
"""
Deployment readiness verification script

Checks if the application is ready for production deployment
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_environment_variables():
    """Check if required environment variables are configured"""
    print("\n📋 Checking environment variables...")
    
    checks = {
        'SECRET_KEY': os.environ.get('SECRET_KEY'),
        'FLASK_ENV': os.environ.get('FLASK_ENV'),
        'DATABASE_URL (production only)': os.environ.get('DATABASE_URL') or 'N/A (dev mode)',
    }
    
    for var, value in checks.items():
        if value and value != 'N/A (dev mode)':
            print(f"  ✓ {var}: set")
        elif var == 'DATABASE_URL (production only)':
            print(f"  ⚠️  {var}: not set (required for production)")
        else:
            print(f"  ❌ {var}: not set")
    
    return bool(os.environ.get('SECRET_KEY'))


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'werkzeug',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('_', '-'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package}: not installed")
            missing.append(package)
    
    return len(missing) == 0


def check_configuration_files():
    """Check if critical configuration files exist"""
    print("\n📁 Checking configuration files...")
    
    files = {
        'config.py': Path('config.py'),
        'wsgi.py': Path('wsgi.py'),
        '.env.example': Path('.env.example'),
        '.gitignore': Path('.gitignore'),
        'Procfile': Path('Procfile'),
        'runtime.txt': Path('runtime.txt'),
        'Dockerfile': Path('Dockerfile'),
    }
    
    all_exist = True
    for name, path in files.items():
        if path.exists():
            print(f"  ✓ {name}")
        else:
            print(f"  ❌ {name}: missing")
            all_exist = False
    
    return all_exist


def check_security():
    """Check for security issues"""
    print("\n🔒 Checking security...")
    
    issues = []
    
    # Check if .env is in git
    gitignore = Path('.gitignore')
    if gitignore.exists():
        content = gitignore.read_text()
        if '.env' in content:
            print("  ✓ .env is in .gitignore")
        else:
            print("  ⚠️  .env might not be in .gitignore")
            issues.append(".env not in .gitignore")
    
    # Check if SECRET_KEY is hardcoded in code
    try:
        import re
        app_file = Path('app/__init__.py')
        if app_file.exists():
            content = app_file.read_text()
            # Look for hardcoded secrets
            if "SECRET_KEY = '" in content or 'SECRET_KEY = "' in content:
                if 'os.environ' not in content:
                    print("  ❌ Hardcoded SECRET_KEY found in code!")
                    issues.append("Hardcoded SECRET_KEY")
                else:
                    print("  ✓ SECRET_KEY is environment-based")
            else:
                print("  ✓ No hardcoded secrets detected")
    except Exception as e:
        print(f"  ⚠️  Could not scan for hardcoded secrets: {e}")
    
    return len(issues) == 0


def check_database():
    """Check database connectivity"""
    print("\n🗄️  Checking database...")
    
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.extensions import db
            from sqlalchemy import text
            
            # Try to execute a simple query
            db.session.execute(text('SELECT 1'))
            print("  ✓ Database connection successful")
            return True
    except Exception as e:
        print(f"  ⚠️  Database check failed: {str(e)}")
        return False


def check_application_startup():
    """Check if application starts without errors"""
    print("\n🚀 Checking application startup...")
    
    try:
        from app import create_app
        app = create_app()
        print("  ✓ Application initializes successfully")
        
        # Check if blueprints are registered
        blueprints = list(app.blueprints.keys())
        if len(blueprints) > 0:
            print(f"  ✓ {len(blueprints)} blueprints registered")
            return True
        else:
            print("  ⚠️  No blueprints registered")
            return False
    except Exception as e:
        print(f"  ❌ Application startup failed: {e}")
        return False


def check_documentation():
    """Check if deployment documentation exists"""
    print("\n📚 Checking documentation...")
    
    docs = {
        'README.md': Path('README.md'),
        'DEPLOYMENT.md': Path('DEPLOYMENT.md'),
        'DEPLOYMENT_CHECKLIST.md': Path('DEPLOYMENT_CHECKLIST.md'),
        'DEPLOYMENT_DOCKER.md': Path('DEPLOYMENT_DOCKER.md'),
    }
    
    for name, path in docs.items():
        if path.exists():
            print(f"  ✓ {name}")
        else:
            print(f"  ⚠️  {name}: missing")
    
    return all(path.exists() for path in docs.values())


def main():
    """Run all checks"""
    print("=" * 60)
    print("JC Icons Management System - Deployment Readiness Check")
    print("=" * 60)
    
    results = {
        'Environment Variables': check_environment_variables(),
        'Dependencies': check_dependencies(),
        'Configuration Files': check_configuration_files(),
        'Security': check_security(),
        'Database': check_database(),
        'Application': check_application_startup(),
        'Documentation': check_documentation(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ Application is ready for deployment!")
        return 0
    else:
        print("\n⚠️  Please fix the issues above before deploying")
        return 1


if __name__ == '__main__':
    sys.exit(main())
