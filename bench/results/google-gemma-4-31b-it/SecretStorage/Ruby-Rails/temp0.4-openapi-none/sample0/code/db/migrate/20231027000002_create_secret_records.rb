class CreateSecretRecords < ActiveRecord::Migration[8.0]
  def change
    create_table :secret_records do |t|
      t.references :user, null: false, foreign_key: true, index: { unique: true }
      t.text :secret_text
      t.timestamps
    end
  end
end