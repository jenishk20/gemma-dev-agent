class Product < ApplicationRecord
  # name: string
  # properties: text (stored as JSON)

  validates :name, presence: true, uniqueness: true

  # Helper to merge name and properties for search and display
  def full_attributes
    attrs = properties || {}
    attrs.merge("name" => name)
  end

  # Helper to extract properties excluding the name
  def unstructured_properties
    properties || {}
  end
end