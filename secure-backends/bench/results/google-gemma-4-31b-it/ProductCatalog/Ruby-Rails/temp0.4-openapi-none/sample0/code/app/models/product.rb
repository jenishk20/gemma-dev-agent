class Product < ApplicationRecord
  # name: string
  # properties: json (stored as text in sqlite)

  validates :name, presence: true, uniqueness: true

  # Helper to merge name and properties for the API response
  def as_json_with_properties
    result = { name: name }
    result.merge!(properties || {})
    result
  end

  # Search logic: matches name or any value inside the properties JSON
  def self.search(query)
    where("name LIKE ?", "%#{query}%")
      .or(where("properties LIKE ?", "%#{query}%"))
  end
end