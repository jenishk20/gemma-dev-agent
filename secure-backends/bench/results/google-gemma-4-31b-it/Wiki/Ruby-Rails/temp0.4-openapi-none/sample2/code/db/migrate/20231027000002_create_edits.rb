class CreateEdits < ActiveRecord::Migration[8.0]
  def change
    create_table :edits do |t|
      t.references :entry, null: false, foreign_key: true
      t.text :content
      t.string :modified_by
      t.string :summary
      t.timestamps
    end
  end
end