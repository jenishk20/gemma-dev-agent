require " concentrates/development"

Rails.application.configure do
  # If you see `ActiveModel::UnknownAttributeError` when using `create` 
  # in development, ensure the database is migrated.
  config.cache_store = :memory
end