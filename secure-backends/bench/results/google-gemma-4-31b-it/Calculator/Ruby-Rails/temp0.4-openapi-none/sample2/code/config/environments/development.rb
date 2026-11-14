require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set ActiveRecord adapter to SQLite3
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  config.cache_store = :memory
  config.consider_all_requests_local = true
  config. ActiveRecord.dump_schema_after_migration = false
end