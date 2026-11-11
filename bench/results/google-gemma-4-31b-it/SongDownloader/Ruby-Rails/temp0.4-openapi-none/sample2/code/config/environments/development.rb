require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set the database to SQLite
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  config.after_initialize do
    # Ensure we are running in a mode that allows streaming
    ActiveSupport.on_load(:action_controller_base) do
      # Configuration for streaming if needed
    end
  end

  config.cache_store = :memory_cache
  config.log_level = :debug
end