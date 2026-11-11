class CreateProducts < ActiveRecord::Migration[8.0]
  def change
    create_table :products do |t|
      t.string :product_name
      t.text :tags # Store as text for serialization
      t.timestamps
    end
  end
end