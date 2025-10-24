from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ExpaDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expa_data'
    
    def ready(self):
        """Called when Django starts - automatically start the scheduler"""
        try:
            # Import here to avoid circular imports
            from .views import start_auto_sync_scheduler
            
            # Start the scheduler automatically
            if start_auto_sync_scheduler():
                logger.info("🚀 Auto sync scheduler started automatically on Django startup!")
                print("🚀 Auto sync scheduler started automatically - syncing every 12 hours!")
            else:
                logger.info("ℹ️ Auto sync scheduler was already running")
                print("ℹ️ Auto sync scheduler was already running")
                
        except Exception as e:
            logger.error(f"❌ Failed to start auto sync scheduler: {str(e)}")
            print(f"❌ Failed to start auto sync scheduler: {str(e)}")
            # Don't crash the app if scheduler fails to start
            pass
