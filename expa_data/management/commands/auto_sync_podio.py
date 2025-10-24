from django.core.management.base import BaseCommand
from django.core.management import call_command
import time
import schedule
from datetime import datetime

class Command(BaseCommand):
    help = 'Automatically sync 100 Podio records every 12 hours'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Podio Auto-Sync (100 records every 12 hours)')
        )
        
        # Schedule sync every 12 hours
        schedule.every(12).hours.do(self.run_sync)
        
        # Run initial sync
        self.stdout.write(self.style.SUCCESS('🔄 Running initial sync...'))
        self.run_sync()
        
        # Keep the scheduler running
        self.stdout.write(self.style.SUCCESS('⏰ Auto-sync started. Press Ctrl+C to stop.'))
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(300)  # Check every 5 minutes
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⏹️ Auto-sync stopped'))

    def run_sync(self):
        """Run sync for all programmes with 100 records limit"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(f'🔄 Starting sync at {timestamp}')
            
            # Sync all programmes with max 100 items each
            call_command('sync_podio', programme='all', max_items=100, verbosity=1)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sync completed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Sync failed: {str(e)}')
            )