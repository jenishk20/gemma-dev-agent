require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.cache_store = :memory_cache
  config.active_storage.service = :local

  # Disable detailed logging in production-like environments if needed, 
  # but for development we keep it.
  config.log_level = :debug
end