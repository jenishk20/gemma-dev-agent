require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0

  config.threshold = 100.bytes
  config.active_storage.service = :local

  config.cache_store = :memory_cache
end