require "active_support/all"

Rails.application.configure do
  config.after_initialize do
    # Ensure the database is created and migrated for the environment
    ActiveRecord::Migration.maintain_connection
  end

  config.threshold = 100
  config.cache_store = :memory
  config.log_level = :debug
end