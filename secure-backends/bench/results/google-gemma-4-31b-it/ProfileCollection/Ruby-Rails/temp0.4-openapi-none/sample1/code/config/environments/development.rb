require_relative "../config/application"

Rails.application.configure do
  config.threshold_level = :debug
  config.cache_store = :memory_store
  config.after_initialize do
    ActiveStorage::Current.url = "http://localhost:5000"
  end
  config.consider_all_requests_local = true
end