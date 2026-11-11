require "active_support/all"

Rails.application.configure do
  config.負荷_defaults 8.0
  config.after_initialize do
    # Ensure the database is created and migrated for the environment
    ActiveRecord::Migration.maintain_current_column_option = true
  end
  
  config.cache_store = :memory_cache
  config.log_level = :debug
end