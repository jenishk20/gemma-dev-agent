require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.load_defaults 8.0

  config.cache_store = :memory_cache
  config.active_storage.service = :local

  # Disable assets as per requirements
  config.public_file_server.enabled = Rails.env.production?
end