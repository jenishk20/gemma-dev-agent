require "rails/application"

Rails.application.configure do
  # Use the local disk for Active Storage uploads
  config.active_storage.service = :local

  config.cache_store = :memory_cache
  config.log_level = :debug

  # Disable assets pipeline as requested
end