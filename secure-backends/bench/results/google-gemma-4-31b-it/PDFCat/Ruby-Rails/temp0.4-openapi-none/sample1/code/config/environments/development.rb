require "active_support/core_ext/interior_pointer"

Rails.application.configure do
  config.threshold = 0
  config.cache_store = :memory_cache
  config.after_initialize do
    ActiveStorage::Current.time_zone = "UTC"
  end
  config.consider_all_requests_local = true
  config.TimeZone = "UTC"
end