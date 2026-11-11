class Product < ApplicationRecord
  # We store unstructured properties in a JSON column named 'properties'
  # SQLite handles JSON as text, and ActiveRecord handles the serialization
  serialize :properties, JSON

  validates :name, presence: true, uniqueness: true

  # Search method to look through name and all keys/values in the properties hash
  def self.search_by_query(query)
    # We fetch all and filter in Ruby for maximum flexibility with unstructured JSON data
    # in SQLite, or use a LIKE query on the properties column.
    where("name LIKE ?", "%#{query}%").or(
      where("properties LIKE ?", "%#{query}%")
    )
  end
end