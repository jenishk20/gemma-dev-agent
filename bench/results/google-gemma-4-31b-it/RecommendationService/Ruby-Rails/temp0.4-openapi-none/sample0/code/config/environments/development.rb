require "active_support/core_ext/slogging"

Recommendation::Application.configure do
  config.threshold = 100.days

  # Set the database to use db.sqlite3
  config.active_record.database_selector = { delay: 5.seconds }
  config.active_record.database_timeout = 5000
  
  config.cache_store = :memory_store
  config.log_level = :debug
end