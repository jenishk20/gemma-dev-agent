require "active_support/all"

Rails.application.configure do
  config.threshold = 100
  config.cache_store = :memory_store
  config.log_level = :debug
  config.log_formatter = ::Logger::Formatter.new
  config.active_storage.service = :local
end