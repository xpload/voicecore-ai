"""Quick script to add __tablename__ to models that are missing it"""
import re
import os

def fix_tablenames_in_file(filepath):
    """Add __tablename__ to models missing it"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all class definitions that inherit from BaseModel
        pattern = r'(class\s+(\w+)\(.*BaseModel.*\):)\s*\n(\s+""")'
        
        def add_tablename(match):
            class_def = match.group(1)
            class_name = match.group(2)
            indent = match.group(3)
            
            # Convert CamelCase to snake_case for table name
            table_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            
            # Check if __tablename__ already exists in the next few lines
            next_lines = content[match.end():match.end()+200]
            if '__tablename__' in next_lines:
                return match.group(0)  # Already has tablename
            
            return f'{class_def}\n{indent[:-3]}__tablename__ = "{table_name}"\n{indent}'
        
        new_content = re.sub(pattern, add_tablename, content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
            
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

# Fix all model files
model_files = [
    'voicecore/models/knowledge.py',
    'voicecore/models/analytics.py',
    'voicecore/models/voicemail.py',
    'voicecore/models/vip.py',
    'voicecore/models/crm.py',
    'voicecore/models/callback.py',
    'voicecore/models/billing.py',
    'voicecore/models/ai_personality.py',
    'voicecore/models/agent.py',
    'voicecore/models/tenant.py',
    'voicecore/models/security.py',
]

for filepath in model_files:
    if os.path.exists(filepath):
        if fix_tablenames_in_file(filepath):
            print(f"✅ Fixed {filepath}")
        else:
            print(f"⚠️  No changes needed in {filepath}")
    else:
        print(f"❌ File not found: {filepath}")

print("\n✅ All files processed!")
