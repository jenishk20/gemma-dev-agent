require "active_support/all"

Rails.application.configure do
  # If you see ActiveRecord: Migration pending with the system's error message, 
  # run `bin/rails db:migrate`
  config.cache_store = :memory

  # Disable assets as requested
  config.assets.enabled = false
  
  # Ensure we are using the correct database file
  config.active_record.database_selector = { application: :db_sqlite3 }
end