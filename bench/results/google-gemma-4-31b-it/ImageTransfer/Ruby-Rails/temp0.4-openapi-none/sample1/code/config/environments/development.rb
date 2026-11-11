require "active_storage/engine"

Rails.application.configure do
  config.threshold_level_in_bytes = 0
  config.sane_logging_level = :debug

  config.cache_store = :memory_store
  config.active_storage.service = :local

  config.autoload_paths << Rails.root.join("lib")

  config.consider_all_requests_local = true
  config.active_storage.service = :local
end