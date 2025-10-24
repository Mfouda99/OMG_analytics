from django.core.management.base import BaseCommand
from django.test import RequestFactory
from expa_data.views import sync_all_podio_data, sync_podio_ogv, sync_podio_ogta, sync_podio_ogte
import json


class Command(BaseCommand):
    help = 'Sync data from Podio API for OGV, OGTa, and OGTe programmes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--programme',
            type=str,
            choices=['OGV', 'OGTa', 'OGTe', 'all'],
            default='all',
            help='Specify which programme to sync (default: all)',
        )
        parser.add_argument(
            '--max-items',
            type=int,
            default=None,
            help='Maximum number of items to fetch per programme (default: all available)',
        )

    def handle(self, *args, **options):
        programme = options['programme']
        max_items = options.get('max_items')
        factory = RequestFactory()
        
        if max_items:
            self.stdout.write(
                self.style.SUCCESS(f'🚀 Starting Podio sync for {programme} (max {max_items} items)...')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'🚀 Starting Podio sync for {programme}...')
            )

        try:
            if programme == 'all':
                # Sync all programmes
                request = factory.get('/api/sync-all-podio/')
                response = sync_all_podio_data(request)
                
            elif programme == 'OGV':
                request = factory.get('/api/sync-podio-ogv/')
                response = sync_podio_ogv(request, max_items=max_items)
                
            elif programme == 'OGTa':
                request = factory.get('/api/sync-podio-ogta/')
                response = sync_podio_ogta(request, max_items=max_items)
                
            elif programme == 'OGTe':
                request = factory.get('/api/sync-podio-ogte/')
                response = sync_podio_ogte(request, max_items=max_items)

            # Parse response
            if hasattr(response, 'content'):
                result = json.loads(response.content.decode('utf-8'))
                
                if result.get('status') == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {result.get("message", "Sync completed successfully")}')
                    )
                    
                    # Show detailed results for individual programmes
                    if 'new_records' in result:
                        self.stdout.write(f'   📊 New records: {result["new_records"]}')
                        self.stdout.write(f'   📋 Total processed: {result["total_processed"]}')
                    
                    # Show results for all programmes sync
                    if 'results' in result:
                        for prog, prog_result in result['results'].items():
                            if prog_result.get('status') == 'success':
                                self.stdout.write(f'   ✅ {prog}: {prog_result.get("new_records", 0)} new records')
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f'   ❌ {prog}: {prog_result.get("error", "Unknown error")}')
                                )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Sync failed: {result.get("error", "Unknown error")}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Invalid response format')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during sync: {str(e)}')
            )

        self.stdout.write(
            self.style.SUCCESS('🎉 Podio sync process completed!')
        )