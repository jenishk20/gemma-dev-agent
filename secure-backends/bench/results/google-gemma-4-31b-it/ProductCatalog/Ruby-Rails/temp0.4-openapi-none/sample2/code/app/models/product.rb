class Product < ApplicationRecord
  # We use a JSON column 'properties' to store the unstructured data
  # In SQLite, this is stored as a text string and serialized as a Hash
  serialize :properties, JSON

  validates :name, presence: true, uniqueness: true

  # Helper to merge name and properties for the API response
  def to_catalog_hash
    result = { "name" => name }
    result.merge!(properties || {})
    result
  end
end