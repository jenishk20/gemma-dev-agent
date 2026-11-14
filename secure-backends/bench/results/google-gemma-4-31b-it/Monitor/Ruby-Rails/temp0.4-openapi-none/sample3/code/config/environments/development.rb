require "active_model/api"

Rails.application.configure do
  config.lazy_load_time_zone_realtime = false
  config.cache_store = :memory_cache
  config.after_initialize do
    ActiveSupport.time_zone = "UTC"
  end
end