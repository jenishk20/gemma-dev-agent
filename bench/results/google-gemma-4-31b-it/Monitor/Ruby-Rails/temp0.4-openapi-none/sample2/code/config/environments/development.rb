require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set ActiveRecord to use the sqlite3 database
  config.active_record.database_sharing_connection_pool = false
  
  # Disable assets as requested
  config.assets.enabled = false
  
  # Standard development settings
  config.cache_store = :memory_store
  config.log_level = :debug
end