require "rails/environments/development"

ZipToTxt::Application.configure do
  config.threshold = 100.bytes
  config.consider_all_requests_local = true
  config.cache_store = :memory_store
end