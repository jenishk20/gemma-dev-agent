require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.cache_store = :memory_cache
  config.active_storage.service = :local
end