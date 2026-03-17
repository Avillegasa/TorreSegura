#!/usr/bin/env python3
"""
Analizador de dependencias Python - Escanea tu código real
Analiza todos los archivos .py en tu proyecto para determinar dependencias reales
"""

import os
import ast
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict, Counter
import json

class DependencyAnalyzer:
    def __init__(self, project_path='.'):
        self.project_path = Path(project_path)
        self.python_files = []
        self.imports_found = defaultdict(set)
        self.import_locations = defaultdict(list)
        
        # Mapeo de imports a paquetes PyPI
        self.import_to_package = {
            # Django ecosystem
            'django': 'django',
            'rest_framework': 'djangorestframework',
            'crispy_forms': 'django-crispy-forms',
            'crispy_bootstrap4': 'crispy-bootstrap4',
            'crispy_bootstrap5': 'crispy-bootstrap5',
            'allauth': 'django-allauth',
            'environ': 'django-environ',
            'corsheaders': 'django-cors-headers',
            'storages': 'django-storages',
            'extensions': 'django-extensions',
            'debug_toolbar': 'django-debug-toolbar',
            'filter': 'django-filter',
            'taggit': 'django-taggit',
            
            # Data & Science
            'pandas': 'pandas',
            'numpy': 'numpy',
            'scipy': 'scipy',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'plotly': 'plotly',
            'sklearn': 'scikit-learn',
            'cv2': 'opencv-python',
            'PIL': 'pillow',
            'openpyxl': 'openpyxl',
            'xlsxwriter': 'xlsxwriter',
            'xlrd': 'xlrd',
            
            # Web & APIs
            'requests': 'requests',
            'urllib3': 'urllib3',
            'httpx': 'httpx',
            'aiohttp': 'aiohttp',
            'flask': 'flask',
            'fastapi': 'fastapi',
            'starlette': 'starlette',
            'uvicorn': 'uvicorn',
            'gunicorn': 'gunicorn',
            
            # Database
            'psycopg2': 'psycopg2-binary',
            'pymongo': 'pymongo',
            'sqlalchemy': 'sqlalchemy',
            'redis': 'redis',
            'celery': 'celery',
            
            # PDF & Documents
            'reportlab': 'reportlab',
            'PyPDF2': 'pypdf2',
            'fpdf': 'fpdf2',
            'weasyprint': 'weasyprint',
            'xhtml2pdf': 'xhtml2pdf',
            
            # Testing
            'pytest': 'pytest',
            'unittest2': 'unittest2',
            'mock': 'mock',
            'factory': 'factory-boy',
            'faker': 'faker',
            
            # Utilities
            'dateutil': 'python-dateutil',
            'pytz': 'pytz',
            'dotenv': 'python-dotenv',
            'yaml': 'pyyaml',
            'toml': 'toml',
            'click': 'click',
            'rich': 'rich',
            'tqdm': 'tqdm',
            'colorama': 'colorama',
            
            # Crypto & Security
            'cryptography': 'cryptography',
            'jwt': 'pyjwt',
            'bcrypt': 'bcrypt',
            'passlib': 'passlib',
            
            # Image processing
            'cv2': 'opencv-python',
            'skimage': 'scikit-image',
            'imageio': 'imageio',
            
            # Async
            'asyncio': None,  # Built-in
            'aiofiles': 'aiofiles',
            'asyncpg': 'asyncpg',
        }
        
        # Built-in modules (no need to install)
        self.builtin_modules = {
            'os', 'sys', 'json', 'datetime', 'time', 'math', 'random', 're',
            'collections', 'itertools', 'functools', 'operator', 'pathlib',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
            'logging', 'argparse', 'configparser', 'hashlib', 'base64',
            'pickle', 'copy', 'io', 'threading', 'multiprocessing', 'queue',
            'socket', 'ssl', 'ftplib', 'smtplib', 'poplib', 'imaplib',
            'asyncio', 'concurrent', 'subprocess', 'shutil', 'glob', 'fnmatch',
            'tempfile', 'gzip', 'zipfile', 'tarfile', 'uuid', 'secrets',
            'string', 'textwrap', 'unicodedata', 'codecs', 'locale',
            'calendar', 'heapq', 'bisect', 'array', 'weakref', 'types',
            'inspect', 'dis', 'gc', 'site', 'sysconfig', 'platform',
            # Módulos que causaron problemas en tu análisis
            'ast', 'decimal', 'hmac', 'traceback', 'unittest', 'warnings',
            'importlib', 'pkgutil', 'modulefinder', 'runpy', 'token', 'keyword',
        }

    def find_python_files(self):
        """Encuentra todos los archivos Python en el proyecto"""
        exclude_dirs = {
            '__pycache__', '.git', '.vscode', '.idea', 'node_modules',
            'venv', 'env', '.env', 'migrations', '.pytest_cache',
            'htmlcov', '.coverage', 'dist', 'build', '*.egg-info'
        }
        
        exclude_files = {
            'manage.py', 'wsgi.py', 'asgi.py', 'conftest.py'
        }
        
        for root, dirs, files in os.walk(self.project_path):
            # Filtrar directorios excluidos
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py') and file not in exclude_files:
                    file_path = Path(root) / file
                    self.python_files.append(file_path)
        
        print(f"📁 Archivos Python encontrados: {len(self.python_files)}")
        return self.python_files

    def extract_imports_from_file(self, file_path):
        """Extrae imports de un archivo Python específico"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            file_imports = set()
            
            # Método 1: AST parsing (más preciso)
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            file_imports.add(module)
                            self.import_locations[module].append(str(file_path))
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            file_imports.add(module)
                            self.import_locations[module].append(str(file_path))
            
            except SyntaxError:
                # Método 2: Regex backup para archivos con errores de sintaxis
                patterns = [
                    r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        file_imports.add(match)
                        self.import_locations[match].append(str(file_path))
            
            self.imports_found[str(file_path)] = file_imports
            return file_imports
            
        except Exception as e:
            print(f"⚠️  Error procesando {file_path}: {e}")
            return set()

    def get_installed_packages(self):
        """Obtiene paquetes instalados en el entorno actual"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                capture_output=True, text=True, check=True
            )
            
            installed = {}
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    name, version = line.split('==', 1)
                    installed[name.lower().replace('_', '-')] = version
            
            return installed
        except Exception as e:
            print(f"⚠️  Error obteniendo paquetes instalados: {e}")
            return {}

    def parse_requirements_file(self, req_file='requirements.txt'):
        """Parse archivo requirements.txt con múltiples encodings"""
        req_path = self.project_path / req_file
        if not req_path.exists():
            print(f"📄 Archivo {req_file} no encontrado")
            return {}
        
        requirements = {}
        
        # Intentar múltiples encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(req_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Si el contenido está vacío o es binario, intentar siguiente encoding
                    if not content.strip() or '\x00' in content:
                        continue
                        
                for line_num, line in enumerate(content.splitlines(), 1):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Parse diferentes formatos
                        match = re.match(r'^([a-zA-Z0-9_-]+)([><=!~]+.*)?', line)
                        if match:
                            package = match.group(1).lower().replace('_', '-')
                            version = match.group(2) if match.group(2) else ''
                            requirements[package] = {
                                'version': version,
                                'line': line_num,
                                'raw': line
                            }
                break  # Si llegamos aquí, el encoding funcionó
                
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                print(f"⚠️  Error leyendo {req_file} con encoding {encoding}: {e}")
                continue
        
        if not requirements:
            print(f"⚠️  No se pudo leer {req_file} o está vacío")
        else:
            print(f"📄 Requirements.txt leído correctamente ({len(requirements)} paquetes)")
        
        return requirements

    def analyze_dependencies(self):
        """Análisis principal"""
        print("🔍 ANALIZANDO DEPENDENCIAS DEL PROYECTO")
        print("=" * 50)
        
        # 1. Escanear archivos
        self.find_python_files()
        
        # 2. Extraer imports
        all_imports = set()
        print("\n📥 Extrayendo imports...")
        for file_path in self.python_files:
            imports = self.extract_imports_from_file(file_path)
            all_imports.update(imports)
        
        # 3. Clasificar imports
        external_imports = set()
        builtin_imports = set()
        local_imports = set()
        
        for imp in all_imports:
            if imp in self.builtin_modules:
                builtin_imports.add(imp)
            elif self.is_local_import(imp):
                local_imports.add(imp)
            else:
                external_imports.add(imp)
        
        # 4. Mapear a paquetes PyPI
        required_packages = {}
        for imp in external_imports:
            package = self.import_to_package.get(imp, imp.replace('_', '-'))
            if package:  # Ignorar None (built-ins mal clasificados)
                required_packages[package] = imp
        
        # 5. Obtener estado actual
        installed = self.get_installed_packages()
        requirements = self.parse_requirements_file()
        
        # 6. Análisis comparativo
        self.print_analysis_results(
            all_imports, external_imports, builtin_imports, local_imports,
            required_packages, installed, requirements
        )
        
        return {
            'external_imports': external_imports,
            'required_packages': required_packages,
            'installed': installed,
            'requirements': requirements
        }

    def is_local_import(self, module_name):
        """Determina si un import es local al proyecto"""
        # Buscar archivos/directorios con ese nombre
        potential_paths = [
            self.project_path / f"{module_name}.py",
            self.project_path / module_name,
        ]
        
        for app_dir in self.project_path.iterdir():
            if app_dir.is_dir() and not app_dir.name.startswith('.'):
                potential_paths.extend([
                    app_dir / f"{module_name}.py",
                    app_dir / module_name,
                ])
        
        return any(path.exists() for path in potential_paths)

    def print_analysis_results(self, all_imports, external_imports, builtin_imports, 
                             local_imports, required_packages, installed, requirements):
        """Imprime resultados del análisis"""
        
        print(f"\n📊 RESUMEN DE IMPORTS:")
        print(f"   Total imports encontrados: {len(all_imports)}")
        print(f"   • Built-in modules: {len(builtin_imports)}")
        print(f"   • Módulos locales: {len(local_imports)}")
        print(f"   • Paquetes externos: {len(external_imports)}")
        
        print(f"\n📦 PAQUETES REQUERIDOS (según código):")
        for package, import_name in sorted(required_packages.items()):
            status = "✅" if package in installed else "❌"
            in_req = "📄" if package in requirements else "⚠️"
            print(f"   {status} {in_req} {package:<25} (import {import_name})")
        
        print(f"\n📋 ANÁLISIS DE REQUIREMENTS.TXT:")
        if requirements:
            missing_in_code = set(requirements.keys()) - set(required_packages.keys())
            missing_in_req = set(required_packages.keys()) - set(requirements.keys())
            
            if missing_in_req:
                print(f"   ❌ FALTAN EN REQUIREMENTS ({len(missing_in_req)}):")
                for pkg in sorted(missing_in_req):
                    import_name = required_packages[pkg]
                    files = self.import_locations.get(import_name, [])[:3]
                    files_str = ", ".join(Path(f).name for f in files)
                    if len(self.import_locations.get(import_name, [])) > 3:
                        files_str += "..."
                    print(f"      • {pkg} (usado en: {files_str})")
            
            if missing_in_code:
                print(f"   ⚠️  EN REQUIREMENTS PERO NO EN CÓDIGO ({len(missing_in_code)}):")
                for pkg in sorted(missing_in_code):
                    print(f"      • {pkg} - {requirements[pkg]['raw']}")
            
            if not missing_in_req and not missing_in_code:
                print(f"   ✅ Requirements.txt está sincronizado con el código")
        
        print(f"\n🔧 COMANDOS SUGERIDOS:")
        
        # Filtrar paquetes que realmente necesitan instalación
        missing_packages = []
        for pkg in required_packages.keys():
            if pkg not in installed and pkg not in self.builtin_modules:
                missing_packages.append(pkg)
        
        if missing_packages:
            print(f"   # Instalar paquetes faltantes:")
            print(f"   pip install {' '.join(missing_packages)}")
        else:
            print(f"   ✅ Todos los paquetes necesarios están instalados")
        
        # Solo sugerir agregar a requirements si realmente falta
        missing_in_req = set(required_packages.keys()) - set(requirements.keys())
        # Filtrar built-ins
        missing_in_req = {pkg for pkg in missing_in_req if required_packages[pkg] not in self.builtin_modules}
        
        if missing_in_req:
            print(f"\n   # Agregar a requirements.txt:")
            for pkg in sorted(missing_in_req):
                if pkg in installed:
                    version = installed[pkg]
                    print(f"   echo '{pkg}=={version}' >> requirements.txt")
                else:
                    print(f"   # {pkg} (instalar primero para obtener versión)")
        else:
            print(f"\n   ✅ Todos los paquetes necesarios están en requirements.txt")
        
        print(f"\n📈 HERRAMIENTAS ADICIONALES:")
        print(f"   pip install pipdeptree pip-audit safety")
        print(f"   pipdeptree                    # Ver árbol de dependencias")
        print(f"   pip-audit                     # Vulnerabilidades")
        print(f"   safety check                  # Security check")

    def generate_clean_requirements(self, output_file='requirements_clean.txt'):
        """Genera un requirements.txt limpio basado en el código"""
        analysis = self.analyze_dependencies()
        installed = analysis['installed']
        required_packages = analysis['required_packages']
        
        output_path = self.project_path / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Generated by dependency analyzer\n")
            f.write("# Based on actual imports in code\n\n")
            
            for package in sorted(required_packages.keys()):
                if package in installed:
                    f.write(f"{package}=={installed[package]}\n")
                else:
                    f.write(f"# {package}  # NOT INSTALLED\n")
        
        print(f"\n💾 Archivo generado: {output_file}")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analiza dependencias de proyecto Python')
    parser.add_argument('--path', default='.', help='Ruta del proyecto (default: .)')
    parser.add_argument('--generate', action='store_true', 
                       help='Genera requirements_clean.txt')
    
    args = parser.parse_args()
    
    analyzer = DependencyAnalyzer(args.path)
    analyzer.analyze_dependencies()
    
    if args.generate:
        analyzer.generate_clean_requirements()

if __name__ == "__main__":
    main()