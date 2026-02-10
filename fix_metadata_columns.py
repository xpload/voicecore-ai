"""Quick script to fix metadata column names in all model files"""
import re

files_to_fix = [
    ('voicecore/models/analytics.py', 'metrics_metadata'),
    ('voicecore/models/voicemail.py', 'vm_metadata'),
    ('voicecore/models/vip.py', 'vip_metadata'),
    ('voicecore/models/crm.py', 'crm_metadata'),
    ('voicecore/models/callback.py', 'callback_metadata'),
    ('voicecore/models/billing.py', 'billing_metadata'),
    ('voicecore/models/ai_personality.py', 'personality_metadata'),
]

for filepath, new_name in files_to_fix:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace metadata = Column( with new_name = Column("metadata",
        pattern = r'(\s+)metadata\s*=\s*Column\('
        replacement = rf'\1{new_name} = Column("metadata", '
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Fixed {filepath}")
        else:
            print(f"⚠️  No changes needed in {filepath}")
            
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

print("\n✅ All files processed!")
