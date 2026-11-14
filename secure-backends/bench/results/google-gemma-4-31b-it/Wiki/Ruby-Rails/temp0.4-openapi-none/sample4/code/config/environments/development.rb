require "active_support/all"

WikiApp::Application.configure do
  config.after_initialize do
    # Ensure the database is created and migrated for the environment
    ActiveRecord::Migration.maintain_lock_timeout = 5
  end

  config.cache_store = :memory_cache
  config. autoload_paths << Rails.root.join("lib")
end