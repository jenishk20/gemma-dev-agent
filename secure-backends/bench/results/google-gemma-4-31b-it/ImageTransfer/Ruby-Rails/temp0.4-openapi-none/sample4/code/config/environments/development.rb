require "active_storage/engine"

ImageShareApi::Application.configure do
  config.threshold = 100.bytes

  # Configure Active Storage to use the local disk
  config.active_storage.service = :local

  config.rails_serve_static_assets = true

  if ENV["RAILS_ENV"] == "development"
    config.cache_store = :memory_cache
  end
end