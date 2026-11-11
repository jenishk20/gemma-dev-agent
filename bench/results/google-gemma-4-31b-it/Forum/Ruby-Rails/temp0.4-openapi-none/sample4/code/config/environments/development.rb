require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 500
  config.cache_store = :memory_store
  config.log_level = :debug
  config.active_storage.service = :local

  # Ensure the app doesn't try to use asset pipeline as per requirements
  config.public_file_server.enabled = true
end