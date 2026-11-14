require "active_support/core_ext/slogging"

Rails.application.configure do
  config.load_defaults 8.0

  config.server.url = "http://localhost:5000"
  config.api_only = true

  # Disable caching for development
  config.cache_store = :memory_cache
  config.active_storage.service = :local
end