#!/usr/bin/env python3
"""Automated Backup Manager for BotPolyMarket

Features:
- Scheduled backups (hourly, daily, weekly)
- Database backup (trades, positions, performance)
- Configuration files backup
- Logs backup
- Compression and encryption
- Retention policy (keep last N backups)
- Cloud storage support (S3, GCS)
- Restore functionality
- Backup verification

Author: juankaspain
Version: 7.0
"""
import os
import sys
import shutil
import tarfile
import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
import schedule
import time
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups for BotPolyMarket"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config.get('backup_dir', 'backups'))
        self.data_dir = Path(config.get('data_dir', 'data'))
        self.config_dir = Path(config.get('config_dir', 'config'))
        self.logs_dir = Path(config.get('logs_dir', 'logs'))
        
        # Backup settings
        self.retention_days = config.get('backup_retention_days', 30)
        self.enable_encryption = config.get('enable_backup_encryption', True)
        self.enable_compression = config.get('enable_backup_compression', True)
        self.cloud_storage = config.get('cloud_storage_enabled', False)
        self.cloud_provider = config.get('cloud_provider', 's3')  # s3, gcs, azure
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption key
        self.encryption_key = self._load_or_create_key()
        
        logger.info(f"BackupManager initialized. Backup dir: {self.backup_dir}")
    
    def _load_or_create_key(self) -> bytes:
        """Load or create encryption key"""
        key_file = self.config_dir / '.backup_key'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            key_file.chmod(0o600)  # Restrict permissions
            logger.info("Created new backup encryption key")
            return key
    
    def create_backup(self, backup_type: str = 'full') -> Dict:
        """Create a new backup
        
        Args:
            backup_type: 'full', 'incremental', 'database', 'config'
        
        Returns:
            Dict with backup metadata
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"Creating {backup_type} backup: {backup_name}")
        
        try:
            # Create temp directory for backup files
            temp_dir = self.backup_dir / f"temp_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            files_backed_up = []
            
            # Backup database files
            if backup_type in ['full', 'database']:
                db_files = self._backup_database(temp_dir)
                files_backed_up.extend(db_files)
            
            # Backup configuration files
            if backup_type in ['full', 'config']:
                config_files = self._backup_config(temp_dir)
                files_backed_up.extend(config_files)
            
            # Backup logs
            if backup_type == 'full':
                log_files = self._backup_logs(temp_dir)
                files_backed_up.extend(log_files)
            
            # Create tarball
            tar_path = backup_path.with_suffix('.tar.gz' if self.enable_compression else '.tar')
            self._create_archive(temp_dir, tar_path)
            
            # Encrypt if enabled
            if self.enable_encryption:
                encrypted_path = self._encrypt_file(tar_path)
                tar_path.unlink()  # Remove unencrypted file
                final_path = encrypted_path
            else:
                final_path = tar_path
            
            # Calculate checksum
            checksum = self._calculate_checksum(final_path)
            
            # Get file size
            file_size = final_path.stat().st_size
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            # Create metadata
            metadata = {
                'backup_name': backup_name,
                'backup_type': backup_type,
                'timestamp': timestamp,
                'file_path': str(final_path),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 ** 2), 2),
                'checksum': checksum,
                'encrypted': self.enable_encryption,
                'compressed': self.enable_compression,
                'files_count': len(files_backed_up),
                'files': files_backed_up
            }
            
            # Save metadata
            self._save_metadata(metadata)
            
            # Upload to cloud if enabled
            if self.cloud_storage:
                self._upload_to_cloud(final_path, metadata)
            
            logger.info(f"Backup created successfully: {final_path}")
            logger.info(f"Size: {metadata['file_size_mb']} MB, Files: {len(files_backed_up)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            raise
    
    def _backup_database(self, dest_dir: Path) -> List[str]:
        """Backup database files"""
        db_backup_dir = dest_dir / 'database'
        db_backup_dir.mkdir(parents=True, exist_ok=True)
        
        files = []
        
        # Backup SQLite database
        db_file = self.data_dir / 'trades.db'
        if db_file.exists():
            shutil.copy2(db_file, db_backup_dir / 'trades.db')
            files.append('database/trades.db')
        
        # Backup JSON data files
        for json_file in self.data_dir.glob('*.json'):
            shutil.copy2(json_file, db_backup_dir / json_file.name)
            files.append(f'database/{json_file.name}')
        
        logger.debug(f"Backed up {len(files)} database files")
        return files
    
    def _backup_config(self, dest_dir: Path) -> List[str]:
        """Backup configuration files"""
        config_backup_dir = dest_dir / 'config'
        config_backup_dir.mkdir(parents=True, exist_ok=True)
        
        files = []
        
        # Backup .env file (excluding sensitive keys)
        env_file = Path('.env')
        if env_file.exists():
            sanitized_env = self._sanitize_env_file(env_file)
            with open(config_backup_dir / '.env', 'w') as f:
                f.write(sanitized_env)
            files.append('config/.env')
        
        # Backup config YAML/JSON files
        if self.config_dir.exists():
            for config_file in self.config_dir.glob('*.yaml'):
                shutil.copy2(config_file, config_backup_dir / config_file.name)
                files.append(f'config/{config_file.name}')
            
            for config_file in self.config_dir.glob('*.json'):
                shutil.copy2(config_file, config_backup_dir / config_file.name)
                files.append(f'config/{config_file.name}')
        
        logger.debug(f"Backed up {len(files)} config files")
        return files
    
    def _backup_logs(self, dest_dir: Path) -> List[str]:
        """Backup log files (recent only)"""
        logs_backup_dir = dest_dir / 'logs'
        logs_backup_dir.mkdir(parents=True, exist_ok=True)
        
        files = []
        cutoff_date = datetime.now() - timedelta(days=7)
        
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob('*.log'):
                # Only backup recent logs
                if datetime.fromtimestamp(log_file.stat().st_mtime) > cutoff_date:
                    shutil.copy2(log_file, logs_backup_dir / log_file.name)
                    files.append(f'logs/{log_file.name}')
        
        logger.debug(f"Backed up {len(files)} log files")
        return files
    
    def _sanitize_env_file(self, env_file: Path) -> str:
        """Remove sensitive information from .env file"""
        sensitive_keys = ['PRIVATE_KEY', 'SECRET', 'PASSWORD', 'TOKEN']
        
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        sanitized = []
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if any(s in key.upper() for s in sensitive_keys):
                    sanitized.append(f"{key}=*** REDACTED ***\n")
                else:
                    sanitized.append(line)
            else:
                sanitized.append(line)
        
        return ''.join(sanitized)
    
    def _create_archive(self, source_dir: Path, dest_file: Path):
        """Create tar archive (with optional compression)"""
        mode = 'w:gz' if self.enable_compression else 'w'
        
        with tarfile.open(dest_file, mode) as tar:
            tar.add(source_dir, arcname=source_dir.name)
        
        logger.debug(f"Created archive: {dest_file}")
    
    def _encrypt_file(self, file_path: Path) -> Path:
        """Encrypt backup file"""
        fernet = Fernet(self.encryption_key)
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = fernet.encrypt(data)
        
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        logger.debug(f"Encrypted backup: {encrypted_path}")
        return encrypted_path
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _save_metadata(self, metadata: Dict):
        """Save backup metadata"""
        metadata_file = self.backup_dir / f"{metadata['backup_name']}_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Also append to backup log
        log_file = self.backup_dir / 'backup_log.json'
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = {'backups': []}
        
        log_data['backups'].append(metadata)
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def _upload_to_cloud(self, file_path: Path, metadata: Dict):
        """Upload backup to cloud storage"""
        try:
            if self.cloud_provider == 's3':
                self._upload_to_s3(file_path, metadata)
            elif self.cloud_provider == 'gcs':
                self._upload_to_gcs(file_path, metadata)
            else:
                logger.warning(f"Cloud provider {self.cloud_provider} not implemented")
        except Exception as e:
            logger.error(f"Cloud upload failed: {e}")
    
    def _upload_to_s3(self, file_path: Path, metadata: Dict):
        """Upload to AWS S3"""
        import boto3
        
        s3_bucket = self.config.get('s3_bucket')
        s3_prefix = self.config.get('s3_prefix', 'botpolymarket/backups')
        
        s3 = boto3.client('s3')
        s3_key = f"{s3_prefix}/{file_path.name}"
        
        s3.upload_file(
            str(file_path),
            s3_bucket,
            s3_key,
            ExtraArgs={'Metadata': {'checksum': metadata['checksum']}}
        )
        
        logger.info(f"Uploaded to S3: s3://{s3_bucket}/{s3_key}")
    
    def restore_backup(self, backup_name: str, restore_path: Optional[Path] = None) -> bool:
        """Restore from backup
        
        Args:
            backup_name: Name of backup to restore
            restore_path: Optional custom restore path
        
        Returns:
            bool: True if successful
        """
        logger.info(f"Restoring backup: {backup_name}")
        
        try:
            # Find backup file
            backup_files = list(self.backup_dir.glob(f"{backup_name}*"))
            backup_file = None
            
            for f in backup_files:
                if f.suffix in ['.tar', '.gz', '.enc'] and 'metadata' not in f.name:
                    backup_file = f
                    break
            
            if not backup_file:
                logger.error(f"Backup file not found: {backup_name}")
                return False
            
            # Load metadata
            metadata_file = self.backup_dir / f"{backup_name}_metadata.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Verify checksum
            if not self._verify_backup(backup_file, metadata['checksum']):
                logger.error("Backup verification failed")
                return False
            
            # Decrypt if needed
            if metadata['encrypted']:
                backup_file = self._decrypt_file(backup_file)
            
            # Extract archive
            restore_dir = restore_path or Path('restore') / backup_name
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(backup_file, 'r:gz' if metadata['compressed'] else 'r') as tar:
                tar.extractall(restore_dir)
            
            logger.info(f"Backup restored to: {restore_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}", exc_info=True)
            return False
    
    def _verify_backup(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify backup integrity"""
        actual_checksum = self._calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    
    def _decrypt_file(self, file_path: Path) -> Path:
        """Decrypt backup file"""
        fernet = Fernet(self.encryption_key)
        
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = fernet.decrypt(encrypted_data)
        
        decrypted_path = file_path.with_suffix('')
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)
        
        return decrypted_path
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        removed_count = 0
        for backup_file in self.backup_dir.glob('backup_*'):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                backup_file.unlink()
                removed_count += 1
                logger.debug(f"Removed old backup: {backup_file.name}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old backups")
    
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        log_file = self.backup_dir / 'backup_log.json'
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            return log_data.get('backups', [])
        else:
            return []
    
    def schedule_backups(self):
        """Schedule automatic backups"""
        # Hourly incremental backups
        schedule.every().hour.do(lambda: self.create_backup('incremental'))
        
        # Daily full backups at 2 AM
        schedule.every().day.at("02:00").do(lambda: self.create_backup('full'))
        
        # Weekly cleanup
        schedule.every().sunday.at("03:00").do(self.cleanup_old_backups)
        
        logger.info("Backup schedule configured")
        
        # Run scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """CLI for backup manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BotPolyMarket Backup Manager')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup', 'schedule'])
    parser.add_argument('--type', default='full', choices=['full', 'incremental', 'database', 'config'])
    parser.add_argument('--name', help='Backup name for restore')
    
    args = parser.parse_args()
    
    # Load config
    config = {
        'backup_dir': 'backups',
        'data_dir': 'data',
        'config_dir': 'config',
        'logs_dir': 'logs',
        'backup_retention_days': 30
    }
    
    manager = BackupManager(config)
    
    if args.action == 'backup':
        metadata = manager.create_backup(args.type)
        print(json.dumps(metadata, indent=2))
    
    elif args.action == 'restore':
        if not args.name:
            print("Error: --name required for restore")
            sys.exit(1)
        success = manager.restore_backup(args.name)
        sys.exit(0 if success else 1)
    
    elif args.action == 'list':
        backups = manager.list_backups()
        print(json.dumps(backups, indent=2))
    
    elif args.action == 'cleanup':
        manager.cleanup_old_backups()
    
    elif args.action == 'schedule':
        print("Starting backup scheduler...")
        manager.schedule_backups()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
