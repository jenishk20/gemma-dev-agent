require "activesupport/all"

Rails.application.configure do
  config.threshold = 5000
  config.timezone_offset = 0
  config.env_file = ".env"

  if config.respond_to?(:force_ssl)
    config.force_ssl = false
  end

  config.cache_store = :memory_store
end