from celery import shared_task
from spatial_server.hloc_localization.map_creation import map_creator
from spatial_server.server import shared_data
from spatial_server import load_cache
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def create_map_from_video_task(self, video_path, num_frames_perc, log_filepath, dataset_name):
    try:
        logger.info(f"Starting create_map_from_video with video_path: {video_path}")
        map_creator.create_map_from_video(video_path, num_frames_perc, log_filepath)
        load_cache.load_db_data(shared_data)
        logger.info(f"Completed create_map_from_video for dataset: {dataset_name}")
    except Exception as exc:
        logger.error(f"create_map_from_video failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def create_map_from_images_task(self, images_folder_path, dataset_name):
    try:
        logger.info(f"Starting create_map_from_images with images_folder_path: {images_folder_path}")
        map_creator.create_map_from_images(images_folder_path)
        load_cache.load_db_data(shared_data)
        logger.info(f"Completed create_map_from_images for dataset: {dataset_name}")
    except Exception as exc:
        logger.error(f"create_map_from_images failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def create_map_from_polycam_output_task(self, polycam_directory, log_file_path, dataset_name):
    try:
        logger.info(f"Starting create_map_from_polycam_output with polycam_directory: {polycam_directory}")
        map_creator.create_map_from_polycam_output(polycam_directory, log_file_path)
        load_cache.load_db_data(shared_data)
        logger.info(f"Completed create_map_from_polycam_output for dataset: {dataset_name}")
    except Exception as exc:
        logger.error(f"create_map_from_polycam_output failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def create_map_from_kiri_engine_output_task(self, kiri_directory, dataset_name):
    try:
        logger.info(f"Starting create_map_from_kiri_engine_output with kiri_directory: {kiri_directory}")
        map_creator.create_map_from_kiri_engine_output(kiri_directory)
        load_cache.load_db_data(shared_data)
        logger.info(f"Completed create_map_from_kiri_engine_output for dataset: {dataset_name}")
    except Exception as exc:
        logger.error(f"create_map_from_kiri_engine_output failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
