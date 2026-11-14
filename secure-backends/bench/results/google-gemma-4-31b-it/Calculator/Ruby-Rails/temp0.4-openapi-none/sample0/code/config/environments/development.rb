require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.cache_store = :memory_cache
  config.log_level = :debug

  # Disable assets as requested
  config.public_file_server.enabled = true
end