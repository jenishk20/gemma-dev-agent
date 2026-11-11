require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 1000
  config.consider_all_requests_local = true
  config.cache_store = :memory_store
end