require "zeitwerk"

ZipToTxt::Application.configure do
  config.load_defaults 8.0

  config.threshold = 1000

  # Use the database-backed adapters for Rails.cache, Active Job, and Action Cable
  config.active_storage.service = :local

  config.active_support.cache = :memory_store

  config.active_job.queue_adapter = :async

  config.autoload_after_restart = false
  config.cmake_generator = "Unix Makefiles"

  config.timezone = "UTC"

  # Set coinage to development
  config.cache_store = "solid_cache_store"
end