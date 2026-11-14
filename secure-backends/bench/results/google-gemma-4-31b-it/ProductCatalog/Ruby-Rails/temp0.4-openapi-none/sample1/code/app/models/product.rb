class Product < ApplicationRecord
  # We use a JSON column 'properties' to store unstructured data
  # In SQLite, this is stored as a string and serialized/deserialized by Rails
  serialize :properties, JSON

  validates :name, presence: true, uniqueness: true

  # Helper to merge name into the properties hash for API responses
  def as_json_with_properties
    result = self.properties || {}
    result["name"] = self.name
    result
  end
end