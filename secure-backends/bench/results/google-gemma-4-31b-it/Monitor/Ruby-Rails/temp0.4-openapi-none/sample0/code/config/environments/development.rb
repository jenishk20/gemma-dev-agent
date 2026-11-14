require "active_support/all"

MonitorService::Application.configure do
  config.threshold = 5
  config.cache_store = :memory_cache
  config.log_level = :debug

  config.active_storage.service = :local

  # Set codebase to be used for assets
  config.public_file_server.enabled = true
end